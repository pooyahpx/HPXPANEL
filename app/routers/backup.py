from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse

from app.db import AsyncSession, get_db
from app.models.admin import AdminDetails
from app.models.backup import (
    BackupConfig,
    BackupInstallTokenRequest,
    BackupInstallTokenResponse,
    BackupInstallTokensResponse,
    BackupInstallTokenUpdate,
    BackupListResponse,
    BackupRestoreResponse,
    BackupRunResponse,
)
from app.operation import OperatorType
from app.operation.backup import BackupOperation
from app.rate_limit import normalize_client_ip
from app.utils import responses
from app.utils.check_host_geo import lookup_check_host_ip

from .authentication import require_permission

router = APIRouter(tags=["Backup"], prefix="/api/backup", responses={401: responses._401, 403: responses._403})
public_router = APIRouter(tags=["Backup"], prefix="/api/public")
backup_operator = BackupOperation(operator_type=OperatorType.API)


def _require_owner(admin: AdminDetails = Depends(require_permission("settings", "update"))) -> AdminDetails:
    if not admin.is_owner:
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


@router.get("/install-tokens", response_model=BackupInstallTokensResponse)
async def list_backup_install_tokens(
    _: AdminDetails = Depends(_require_owner),
):
    return backup_operator.list_install_tokens()


@router.patch("/install-tokens/{token}")
async def update_backup_install_token(
    token: str,
    payload: BackupInstallTokenUpdate,
    _: AdminDetails = Depends(_require_owner),
):
    return backup_operator.set_install_token_enabled(token, enabled=payload.enabled)


@router.post("/install-tokens/{token}/revoke")
async def revoke_backup_install_token(
    token: str,
    _: AdminDetails = Depends(_require_owner),
):
    return backup_operator.revoke_install_token(token)


@router.get("/{backup_id}/download")
async def download_panel_backup(
    backup_id: str,
    _: AdminDetails = Depends(require_permission("settings", "read")),
):
    path = backup_operator.download_path(backup_id)
    return FileResponse(path, filename=path.name, media_type="application/zip")


@router.post("/{backup_id}/install-token", response_model=BackupInstallTokenResponse)
async def create_backup_install_token(
    backup_id: str,
    request: Request,
    payload: BackupInstallTokenRequest | None = None,
    _: AdminDetails = Depends(_require_owner),
):
    """Mint a short-lived token + install command that restores this backup on a new server."""
    body = payload or BackupInstallTokenRequest()
    return backup_operator.create_install_link(
        backup_id,
        panel_base_url=body.panel_base_url or str(request.base_url).rstrip("/"),
        database=body.database,
        ttl_hours=body.ttl_hours,
    )


@router.post("/import", response_model=BackupRunResponse)
async def import_panel_backup(
    file: Annotated[UploadFile, File()],
    db: AsyncSession = Depends(get_db),
    _: AdminDetails = Depends(_require_owner),
):
    return await backup_operator.import_archive(db, file)


@router.post("/{backup_id}/restore", response_model=BackupRestoreResponse)
async def restore_panel_backup(
    backup_id: str,
    dry_run: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    _: AdminDetails = Depends(_require_owner),
):
    try:
        return await backup_operator.restore(db, backup_id, dry_run=dry_run)
    except HTTPException:
        raise
    except Exception as exc:
        # Surface the real reason to the UI (unhandled RuntimeError becomes a blank 500).
        raise HTTPException(status_code=400, detail=str(exc)[:2000] or "Restore failed") from exc


@public_router.get("/install-restore/{token}")
async def public_install_restore_download(token: str, request: Request):
    """Unauthenticated download used by hpxpanel.sh install --restore-url ..."""
    client_ip = normalize_client_ip(request)
    geo_payload: dict = {}
    try:
        info = await lookup_check_host_ip(client_ip)
        if info is not None:
            geo_payload = {
                "country": info.country,
                "country_code": info.country_code,
                "city": info.city,
                "isp": info.isp,
                "asn": info.asn,
            }
    except Exception:
        geo_payload = {}

    try:
        path = backup_operator.resolve_install_token_archive(
            token,
            consume=False,
            ip=client_ip,
            geo=geo_payload,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc
    return FileResponse(path, filename=path.name, media_type="application/zip")
