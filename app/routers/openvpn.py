from fastapi import APIRouter, Depends, Query

from app.db import AsyncSession, get_db
from app.models.admin import AdminDetails
from app.models.openvpn_ops import (
    OpenVPNHealthCheck,
    OpenVPNNodeMonitoringResponse,
    OpenVPNOnboardingRequest,
    OpenVPNOnboardingResponse,
)
from app.operation import OperatorType
from app.operation.openvpn_ops import OpenVPNOperation
from app.utils import responses

from .authentication import require_permission

router = APIRouter(tags=["OpenVPN"], prefix="/api/openvpn", responses={401: responses._401, 403: responses._403})
openvpn_operator = OpenVPNOperation(operator_type=OperatorType.API)


@router.get("/health", response_model=OpenVPNHealthCheck)
async def openvpn_health(
    core_id: int = Query(..., ge=1),
    node_id: int | None = Query(default=None, ge=1),
    user_id: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
    _: AdminDetails = Depends(require_permission("cores", "read")),
):
    return await openvpn_operator.get_health(db, core_id=core_id, node_id=node_id, user_id=user_id)


@router.get("/node/{node_id}/users", response_model=OpenVPNNodeMonitoringResponse)
async def openvpn_node_users(
    node_id: int,
    db: AsyncSession = Depends(get_db),
    _: AdminDetails = Depends(require_permission("nodes", "stats")),
):
    return await openvpn_operator.get_node_monitoring(db, node_id)


@router.post("/onboarding", response_model=OpenVPNOnboardingResponse)
async def openvpn_onboarding(
    payload: OpenVPNOnboardingRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("cores", "create")),
):
    return await openvpn_operator.run_onboarding(db, payload, admin)
