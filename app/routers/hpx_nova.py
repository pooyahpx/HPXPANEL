from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import FileResponse, PlainTextResponse

from app.db import AsyncSession, get_db
from app.models.admin import AdminDetails
from app.models.hpx_nova import (
    HpxNovaActionResponse,
    HpxNovaAgentAckRequest,
    HpxNovaAgentBootstrap,
    HpxNovaAgentClaimRequest,
    HpxNovaAgentConfigResponse,
    HpxNovaAgentHeartbeatRequest,
    HpxNovaCreate,
    HpxNovaResponse,
    HpxNovasResponse,
    HpxNovaUpdate,
)
from app.operation import OperatorType
from app.operation.hpx_nova import HpxNovaOperation
from app.rate_limit import rate_limiter
from app.services.hpx_nova import engine_mirror
from app.utils import responses
from app.utils.helpers import public_base_url_from_request
from config import rate_limit_settings

from .authentication import require_permission

router = APIRouter(
    tags=["HPX Nova"],
    prefix="/api/hpx_nova",
    responses={401: responses._401, 403: responses._403},
)

nova_operator = HpxNovaOperation(operator_type=OperatorType.API)


def _request_base_url(request: Request) -> str:
    return public_base_url_from_request(request)


def _agent_side(x_side: str | None = Header(default=None, alias="X-HPX-Nova-Side")) -> str:
    if x_side not in {"iran", "abroad"}:
        raise HTTPException(status_code=400, detail="X-HPX-Nova-Side must be iran or abroad")
    return x_side


def _agent_key(x_key: str | None = Header(default=None, alias="X-HPX-Nova-Agent-Key")) -> str:
    if not x_key:
        raise HTTPException(status_code=401, detail="Missing X-HPX-Nova-Agent-Key")
    return x_key


@router.get("/engine")
async def get_nova_engine_info(
    _: AdminDetails = Depends(require_permission("hpx_nova", "read")),
):
    return {
        "engine_name": "HPX NOVA TUNNEL ENGINE",
        "engine_version": engine_mirror.engine_version(),
        "release_tag": engine_mirror.release_tag(),
    }


@router.post(
    "",
    response_model=HpxNovaActionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={409: responses._409},
)
async def create_hpx_nova(
    model: HpxNovaCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_nova", "create")),
):
    return await nova_operator.create_nova(db, admin=admin, model=model, panel_url=_request_base_url(request))


@router.get("s", response_model=HpxNovasResponse)
async def list_hpx_novas(
    offset: int = 0,
    limit: int = 50,
    name: str | None = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_nova", "read")),
):
    return await nova_operator.list_novas(db, admin=admin, offset=offset, limit=limit, name=name)


@router.post("/agent/claim", response_model=HpxNovaAgentBootstrap)
async def claim_hpx_nova_agent(
    model: HpxNovaAgentClaimRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await rate_limiter.enforce(
        request,
        "hpx-nova-agent-claim",
        getattr(rate_limit_settings, "pulse_claim_limit", 30),
        getattr(rate_limit_settings, "pulse_claim_window", 60),
        identity=model.join_token,
    )
    return await nova_operator.claim_agent(db, model=model, panel_url=_request_base_url(request))


@router.get("/agent/engine-install.sh", response_class=PlainTextResponse)
async def get_nova_engine_install_script():
    script = engine_mirror.install_script_path()
    if not script.is_file():
        raise HTTPException(status_code=404, detail="Nova engine install script missing")
    return PlainTextResponse(script.read_text(encoding="utf-8"), media_type="text/x-shellscript; charset=utf-8")


@router.get("/agent/hpx-nova-agent.sh", response_class=PlainTextResponse)
async def get_nova_agent_script():
    script = engine_mirror.agent_script_path()
    if not script.is_file():
        raise HTTPException(status_code=404, detail="Nova agent script missing")
    return PlainTextResponse(script.read_text(encoding="utf-8"), media_type="text/x-shellscript; charset=utf-8")


@router.get("/agent/engine/SHA256SUMS", response_class=PlainTextResponse)
async def download_nova_engine_checksums():
    try:
        path = await engine_mirror.ensure_checksums_cached()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch Nova engine checksums: {exc}") from exc
    return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="text/plain; charset=utf-8")


@router.get("/agent/engine/{arch}")
async def download_nova_engine(arch: str):
    try:
        normalized = engine_mirror.normalize_arch(arch)
        path = await engine_mirror.ensure_engine_cached(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch Nova engine: {exc}") from exc
    return FileResponse(path, filename=path.name, media_type="application/gzip")


@router.get("/agent/config", response_model=HpxNovaAgentConfigResponse)
async def get_nova_agent_config(
    db: AsyncSession = Depends(get_db),
    side: str = Depends(_agent_side),
    key: str = Depends(_agent_key),
):
    return await nova_operator.get_agent_config(db, agent_key=key, side=side)


@router.post("/agent/heartbeat")
async def nova_agent_heartbeat(
    model: HpxNovaAgentHeartbeatRequest,
    db: AsyncSession = Depends(get_db),
    side: str = Depends(_agent_side),
    key: str = Depends(_agent_key),
):
    return await nova_operator.agent_heartbeat(db, agent_key=key, side=side, model=model)


@router.post("/agent/ack")
async def nova_agent_ack(
    model: HpxNovaAgentAckRequest,
    db: AsyncSession = Depends(get_db),
    side: str = Depends(_agent_side),
    key: str = Depends(_agent_key),
):
    return await nova_operator.agent_ack(db, agent_key=key, side=side, model=model)


@router.get("/{nova_id}", response_model=HpxNovaResponse)
async def get_hpx_nova(
    nova_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_nova", "read")),
):
    return await nova_operator.get_nova(db, admin=admin, nova_id=nova_id)


@router.patch("/{nova_id}", response_model=HpxNovaActionResponse)
async def update_hpx_nova(
    nova_id: int,
    model: HpxNovaUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_nova", "update")),
):
    return await nova_operator.update_nova(db, admin=admin, nova_id=nova_id, model=model)


@router.delete("/{nova_id}", response_model=HpxNovaActionResponse)
async def delete_hpx_nova(
    nova_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_nova", "delete")),
):
    return await nova_operator.delete_nova(db, admin=admin, nova_id=nova_id)


@router.post("/{nova_id}/join-token", response_model=HpxNovaActionResponse)
async def regenerate_nova_join(
    nova_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_nova", "update")),
):
    return await nova_operator.regenerate_join(
        db, admin=admin, nova_id=nova_id, panel_url=_request_base_url(request)
    )


@router.post("/{nova_id}/sync", response_model=HpxNovaActionResponse)
async def sync_hpx_nova(
    nova_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_nova", "update")),
):
    return await nova_operator.sync_nova(db, admin=admin, nova_id=nova_id)
