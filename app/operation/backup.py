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


def _default_backup_config() -> BackupConfig:
    return BackupConfig()


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
        manifest = await create_backup_async(config, upload_remote=True)
        message = "Backup completed"
        if manifest.remote_error:
            message = f"Backup saved locally; remote upload failed: {manifest.remote_error}"
        return BackupRunResponse(manifest=manifest, message=message)

    async def restore(self, db: AsyncSession, backup_id: str) -> BackupRestoreResponse:
        await restore_backup_async(backup_id)
        return BackupRestoreResponse(
            success=True,
            message="Database restored successfully. Restart the panel to ensure all workers reload cleanly.",
            restart_required=True,
        )

    async def import_archive(self, db: AsyncSession, upload: UploadFile) -> BackupRunResponse:
        from app.backup.service import get_backup_dir

        filename = upload.filename or "imported_backup.zip"
        if not filename.endswith(".zip"):
            raise ValueError("Only .zip backup archives are supported")
        target = get_backup_dir() / filename
        target.write_bytes(await upload.read())
        with zipfile.ZipFile(target) as archive:
            manifest = BackupManifest.model_validate(json.loads(archive.read("manifest.json")))
        return BackupRunResponse(
            manifest=manifest,
            message="Backup archive imported. You can restore it from the list.",
        )

    def download_path(self, backup_id: str):
        from app.backup.service import _resolve_archive

        return _resolve_archive(backup_id)
