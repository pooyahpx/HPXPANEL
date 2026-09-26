from __future__ import annotations

import asyncio
import io
import json
import os
import zipfile

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.backup.service import (
    create_backup_async,
    get_state,
    list_backups,
    start_restore,
    validate_backup_async,
)
from app.db.crud.settings import get_settings, modify_settings
from app.models.backup import (
    BackupConfig,
    BackupInstallTokenResponse,
    BackupListResponse,
    BackupManifest,
    BackupRestoreResponse,
    BackupRunResponse,
    BackupStatus,
)
from app.models.settings import SettingsSchema
from app.operation import BaseOperation
from app.utils.logger import get_logger

logger = get_logger("backup-operation")


def _default_backup_config() -> BackupConfig:
    return BackupConfig()


async def notify_backup_failure(message: str) -> None:
    try:
        from app.db import GetDB
        from app.db.crud.shop import get_owner_admin
        from app.telegram import get_bot

        bot = get_bot()
        if bot is None:
            return
        async with GetDB() as db:
            owner = await get_owner_admin(db)
            if owner is None or not owner.telegram_id:
                return
            await bot.send_message(
                owner.telegram_id,
                f"⚠️ <b>Backup alert</b>\n{message}",
                parse_mode="HTML",
            )
    except Exception:
        logger.debug("Could not send backup failure alert to owner", exc_info=True)


class BackupOperation(BaseOperation):
    async def get_config(self, db: AsyncSession) -> BackupConfig:
        settings = await get_settings(db)
        raw = getattr(settings, "backup", None) or {}
        if not raw:
            return _default_backup_config()
        return BackupConfig.model_validate(raw)

    async def save_config(self, db: AsyncSession, config: BackupConfig) -> BackupConfig:
        db_settings = await get_settings(db)
        modify = SettingsSchema(backup=config)
        await modify_settings(db, db_settings, modify)
        return config

    async def list_backups(self, db: AsyncSession) -> BackupListResponse:
        state = get_state()
        config = await self.get_config(db)
        return BackupListResponse(
            items=list_backups(),
            status=BackupStatus(state.get("status", BackupStatus.idle)),
            last_error=str(state.get("last_error") or ""),
            last_success_at=state.get("last_success_at"),
            config=config,
        )

    async def run_backup(self, db: AsyncSession) -> BackupRunResponse:
        config = await self.get_config(db)
        try:
            manifest = await create_backup_async(config, upload_remote=True)
        except Exception as exc:
            await notify_backup_failure(f"Panel backup failed: {exc}")
            raise
        message = "Backup completed"
        if manifest.remote_error:
            message = f"Backup saved locally; remote upload failed: {manifest.remote_error}"
            await notify_backup_failure(message)
        if manifest.encrypted:
            message = f"{message} (encrypted on disk)"
        return BackupRunResponse(manifest=manifest, message=message)

    async def restore(self, backup_id: str, *, dry_run: bool = False) -> BackupRestoreResponse:
        if dry_run:
            _, checks = await validate_backup_async(backup_id)
            checks = [*checks, "dry-run only — no database writes"]
            return BackupRestoreResponse(
                success=True,
                message="Dry-run passed. Local archive is intact (no remote server is contacted).",
                restart_required=False,
                dry_run=True,
                checks=checks,
            )

        checks, background = await asyncio.to_thread(start_restore, backup_id)
        if background:
            return BackupRestoreResponse(
                success=True,
                message=(
                    "Restore started from the local zip on this server "
                    "(the old panel is not contacted). The panel will bring TimescaleDB/Postgres "
                    "up via Docker and restore in the background — wait about one minute, then refresh. "
                    "If it fails, the error appears under Actions."
                ),
                restart_required=True,
                dry_run=False,
                checks=checks,
            )
        return BackupRestoreResponse(
            success=True,
            message="Database restored successfully. Restart the panel to ensure all workers reload cleanly.",
            restart_required=True,
            dry_run=False,
            checks=checks,
        )

    async def import_archive(self, db: AsyncSession, upload: UploadFile) -> BackupRunResponse:
        from app.backup.crypto import is_encrypted_archive, open_archive_bytes
        from app.backup.service import get_backup_dir

        filename = upload.filename or "imported_backup.zip"
        if not filename.endswith(".zip"):
            raise ValueError("Only .zip backup archives are supported")

        raw = await upload.read()
        # Always store as {manifest.id}.zip — restore / install-token look up by id.
        peek = get_backup_dir() / f".import_{os.getpid()}.zip"
        peek.write_bytes(raw)
        try:
            if is_encrypted_archive(peek):
                payload = open_archive_bytes(peek)
                with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                    manifest = BackupManifest.model_validate(json.loads(archive.read("manifest.json")))
            else:
                with zipfile.ZipFile(peek) as archive:
                    manifest = BackupManifest.model_validate(json.loads(archive.read("manifest.json")))
            target = get_backup_dir() / f"{manifest.id}.zip"
            if peek.resolve() != target.resolve():
                target.write_bytes(raw)
        finally:
            peek.unlink(missing_ok=True)

        return BackupRunResponse(
            manifest=manifest,
            message="Backup archive imported. You can restore it from the list.",
        )

    def download_path(self, backup_id: str):
        from app.backup.service import _resolve_archive

        return _resolve_archive(backup_id)

    def create_install_link(
        self,
        backup_id: str,
        *,
        panel_base_url: str,
        database: str = "timescaledb",
        ttl_hours: int = 72,
    ) -> BackupInstallTokenResponse:
        from datetime import datetime

        from app.backup.install_token import build_install_command, create_install_token

        try:
            row = create_install_token(backup_id, ttl_hours=ttl_hours)
        except FileNotFoundError as exc:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail=str(exc)) from exc

        base = panel_base_url.rstrip("/")
        restore_url = f"{base}/api/public/install-restore/{row['token']}"
        expires = datetime.fromisoformat(str(row["expires_at"]))
        return BackupInstallTokenResponse(
            token=row["token"],
            backup_id=row["backup_id"],
            filename=row["filename"],
            expires_at=expires,
            restore_url=restore_url,
            install_command=build_install_command(restore_url=restore_url, database=database),
        )

    def resolve_install_token_archive(
        self,
        token: str,
        *,
        consume: bool = False,
        ip: str | None = None,
        geo: dict | None = None,
    ):
        from app.backup.install_token import resolve_install_token

        return resolve_install_token(token, consume=consume, ip=ip, geo=geo)

    def list_install_tokens(self):
        from datetime import datetime

        from app.backup.install_token import list_install_tokens
        from app.models.backup import BackupInstallTokenListItem, BackupInstallTokensResponse

        def _dt(value):
            if not value:
                return None
            try:
                return datetime.fromisoformat(str(value))
            except ValueError:
                return None

        items = []
        for row in list_install_tokens(include_revoked=True):
            items.append(
                BackupInstallTokenListItem(
                    token=row["token"],
                    backup_id=row.get("backup_id") or "",
                    filename=row.get("filename") or "",
                    created_at=_dt(row.get("created_at")),
                    expires_at=_dt(row.get("expires_at")),
                    enabled=bool(row.get("enabled", True)),
                    revoked=bool(row.get("revoked")),
                    consumed=bool(row.get("consumed")),
                    use_count=int(row.get("use_count") or 0),
                    last_used_at=_dt(row.get("last_used_at")),
                    last_used_ip=row.get("last_used_ip"),
                    last_used_country=row.get("last_used_country"),
                    last_used_country_code=row.get("last_used_country_code"),
                    last_used_city=row.get("last_used_city"),
                    last_used_isp=row.get("last_used_isp"),
                    last_used_asn=row.get("last_used_asn"),
                )
            )
        return BackupInstallTokensResponse(items=items)

    def set_install_token_enabled(self, token: str, *, enabled: bool):
        from fastapi import HTTPException

        from app.backup.install_token import set_install_token_enabled

        try:
            return set_install_token_enabled(token, enabled=enabled)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=410, detail=str(exc)) from exc

    def revoke_install_token(self, token: str):
        from fastapi import HTTPException

        from app.backup.install_token import revoke_install_token

        try:
            return revoke_install_token(token)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
