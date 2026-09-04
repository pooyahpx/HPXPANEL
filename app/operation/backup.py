from __future__ import annotations

import json
import zipfile

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.backup.service import (
    create_backup_async,
    get_state,
    list_backups,
    restore_backup_async,
)
from app.db.crud.settings import get_settings, modify_settings
from app.models.backup import (
    BackupConfig,
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

    async def restore(self, db: AsyncSession, backup_id: str, *, dry_run: bool = False) -> BackupRestoreResponse:
        checks = await restore_backup_async(backup_id, dry_run=dry_run)
        if dry_run:
            return BackupRestoreResponse(
                success=True,
                message="Dry-run passed. Archive is intact and looks restorable.",
                restart_required=False,
                dry_run=True,
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
        target = get_backup_dir() / filename
        target.write_bytes(await upload.read())
        if is_encrypted_archive(target):
            payload = open_archive_bytes(target)
            with zipfile.ZipFile(__import__("io").BytesIO(payload)) as archive:
                manifest = BackupManifest.model_validate(json.loads(archive.read("manifest.json")))
        else:
            with zipfile.ZipFile(target) as archive:
                manifest = BackupManifest.model_validate(json.loads(archive.read("manifest.json")))
        return BackupRunResponse(
            manifest=manifest,
            message="Backup archive imported. You can restore it from the list.",
        )

    def download_path(self, backup_id: str):
        from app.backup.service import _resolve_archive

        return _resolve_archive(backup_id)
