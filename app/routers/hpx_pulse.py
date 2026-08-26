from fastapi import APIRouter, Depends, Header, Request, status

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
    db: AsyncSession = Depends(get_db),
):
    return await pulse_operator.claim_agent(db, model=model)


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
