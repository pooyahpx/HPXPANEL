from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import FileResponse, PlainTextResponse

from app.db import AsyncSession, get_db
from app.models.admin import AdminDetails
from app.models.hpx_pulse import (
    HpxPulseActionResponse,
    HpxPulseAgentAckRequest,
    HpxPulseAgentBootstrap,
    HpxPulseAgentClaimRequest,
    HpxPulseAgentConfigResponse,
    HpxPulseAgentHeartbeatRequest,
    HpxPulseCreate,
    HpxPulseResponse,
    HpxPulsesResponse,
    PulseAdviseRequest,
    PulseAdviseResponse,
)
from app.operation import OperatorType
from app.operation.hpx_pulse import HpxPulseOperation
from app.services.hpx_pulse import engine_mirror
from app.utils import responses

from .authentication import require_permission

router = APIRouter(
    tags=["HPX Pulse"],
    prefix="/api/hpx_pulse",
    responses={401: responses._401, 403: responses._403},
)

pulse_operator = HpxPulseOperation(operator_type=OperatorType.API)


def _request_base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _agent_side(x_side: str | None = Header(default=None, alias="X-HPX-Pulse-Side")) -> str:
    if x_side not in {"iran", "abroad"}:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="X-HPX-Pulse-Side must be iran or abroad")
    return x_side


def _agent_key(x_key: str | None = Header(default=None, alias="X-HPX-Pulse-Agent-Key")) -> str:
    if not x_key:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Missing X-HPX-Pulse-Agent-Key")
    return x_key


@router.post("/advise", response_model=PulseAdviseResponse)
async def advise_hpx_pulse(
    model: PulseAdviseRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_pulse", "read")),
):
    _ = db
    _ = admin
    return await pulse_operator.advise_pulse(model)


@router.post("", response_model=HpxPulseActionResponse, status_code=status.HTTP_201_CREATED, responses={409: responses._409})
async def create_hpx_pulse(
    model: HpxPulseCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_pulse", "create")),
):
    return await pulse_operator.create_pulse(db, admin=admin, model=model, panel_url=_request_base_url(request))


@router.get("s", response_model=HpxPulsesResponse)
async def list_hpx_pulses(
    offset: int = 0,
    limit: int = 50,
    name: str | None = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_pulse", "read")),
):
    return await pulse_operator.list_pulses(db, admin=admin, offset=offset, limit=limit, name=name)


@router.get("/{pulse_id}", response_model=HpxPulseResponse, responses={404: responses._404})
async def get_hpx_pulse(
    pulse_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_pulse", "read")),
):
    return await pulse_operator.get_pulse(db, admin=admin, pulse_id=pulse_id)


@router.delete("/{pulse_id}", response_model=HpxPulseActionResponse, responses={404: responses._404})
async def delete_hpx_pulse(
    pulse_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_pulse", "delete")),
):
    return await pulse_operator.delete_pulse(db, admin=admin, pulse_id=pulse_id)


@router.post("/{pulse_id}/join-token", response_model=HpxPulseActionResponse, responses={404: responses._404})
async def regenerate_hpx_pulse_tokens(
    pulse_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_pulse", "update")),
):
    return await pulse_operator.regenerate_tokens(
        db, admin=admin, pulse_id=pulse_id, panel_url=_request_base_url(request)
    )


@router.post("/agent/claim", response_model=HpxPulseAgentBootstrap)
async def claim_hpx_pulse_agent(
    model: HpxPulseAgentClaimRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    return await pulse_operator.claim_agent(db, model=model, panel_url=_request_base_url(request))


@router.get("/agent/engine-install.sh", response_class=PlainTextResponse)
async def get_hpx_pulse_engine_install_script():
    script = engine_mirror.install_script_path()
    if not script.is_file():
        raise HTTPException(status_code=404, detail="Engine install script is not bundled with this panel build")
    return PlainTextResponse(script.read_text(encoding="utf-8"), media_type="text/x-shellscript; charset=utf-8")


@router.get("/agent/engine/SHA256SUMS", response_class=PlainTextResponse)
async def download_hpx_pulse_engine_checksums():
    try:
        path = await engine_mirror.ensure_checksums_cached()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch HPX tunnel engine checksums: {exc}") from exc
    return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="text/plain; charset=utf-8")


@router.get("/agent/engine/{arch}")
async def download_hpx_pulse_engine(arch: str):
    try:
        normalized = engine_mirror.normalize_arch(arch)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        path = await engine_mirror.ensure_engine_cached(normalized)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch HPX tunnel engine: {exc}") from exc
    return FileResponse(
        path,
        media_type="application/gzip",
        filename=engine_mirror.asset_name(normalized),
    )


@router.get("/agent/config", response_model=HpxPulseAgentConfigResponse)
async def get_hpx_pulse_agent_config(
    db: AsyncSession = Depends(get_db),
    agent_key: str = Depends(_agent_key),
    side: str = Depends(_agent_side),
):
    return await pulse_operator.get_agent_config(db, agent_key=agent_key, side=side)


@router.post("/agent/heartbeat", response_model=HpxPulseAgentConfigResponse)
async def hpx_pulse_agent_heartbeat(
    model: HpxPulseAgentHeartbeatRequest,
    db: AsyncSession = Depends(get_db),
    agent_key: str = Depends(_agent_key),
    side: str = Depends(_agent_side),
):
    return await pulse_operator.agent_heartbeat(db, agent_key=agent_key, side=side, model=model)


@router.post("/agent/ack", status_code=status.HTTP_204_NO_CONTENT)
async def hpx_pulse_agent_ack(
    model: HpxPulseAgentAckRequest,
    db: AsyncSession = Depends(get_db),
    agent_key: str = Depends(_agent_key),
    side: str = Depends(_agent_side),
):
    await pulse_operator.agent_ack(db, agent_key=agent_key, side=side, model=model)
    return None
