from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

from app.db import AsyncSession, get_db
from app.models.admin import AdminDetails
from app.models.backup import BackupConfig, BackupListResponse, BackupRestoreResponse, BackupRunResponse
from app.operation import OperatorType
from app.operation.backup import BackupOperation
from app.utils import responses

from .authentication import require_permission

router = APIRouter(tags=["Backup"], prefix="/api/backup", responses={401: responses._401, 403: responses._403})
backup_operator = BackupOperation(operator_type=OperatorType.API)


def _require_owner(admin: AdminDetails = Depends(require_permission("settings", "update"))) -> AdminDetails:
    if not admin.is_owner:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Only the owner can manage backups")
    return admin


@router.get("", response_model=BackupListResponse)
async def list_panel_backups(
    db: AsyncSession = Depends(get_db),
    _: AdminDetails = Depends(require_permission("settings", "read")),
):
    return await backup_operator.list_backups(db)


@router.put("/config", response_model=BackupConfig)
async def update_backup_config(
    config: BackupConfig,
    db: AsyncSession = Depends(get_db),
    _: AdminDetails = Depends(_require_owner),
):
    return await backup_operator.save_config(db, config)


@router.post("/run", response_model=BackupRunResponse)
async def run_panel_backup(
    db: AsyncSession = Depends(get_db),
    _: AdminDetails = Depends(_require_owner),
):
    return await backup_operator.run_backup(db)


@router.get("/{backup_id}/download")
async def download_panel_backup(
    backup_id: str,
    _: AdminDetails = Depends(require_permission("settings", "read")),
):
    path = backup_operator.download_path(backup_id)
    return FileResponse(path, filename=path.name, media_type="application/zip")


@router.post("/import", response_model=BackupRunResponse)
async def import_panel_backup(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(_require_owner),
):
    return await backup_operator.import_archive(db, file)


@router.post("/{backup_id}/restore", response_model=BackupRestoreResponse)
async def restore_panel_backup(
    backup_id: str,
    db: AsyncSession = Depends(get_db),
    _: AdminDetails = Depends(_require_owner),
):
    return await backup_operator.restore(db, backup_id)
