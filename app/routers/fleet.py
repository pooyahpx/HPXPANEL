from fastapi import APIRouter, Depends, HTTPException, status

from app.db import AsyncSession, get_db
from app.models.admin import AdminDetails
from app.models.fleet import FleetSummaryResponse
from app.operation import OperatorType
from app.operation.fleet import FleetOperation
from app.operation.permissions import PermissionDenied, enforce_permission
from app.utils import responses

from .authentication import get_current

router = APIRouter(tags=["Fleet"], prefix="/api/fleet", responses={401: responses._401})
fleet_operator = FleetOperation(operator_type=OperatorType.API)


async def require_fleet_read(admin: AdminDetails = Depends(get_current)) -> AdminDetails:
    """Owners/admins with nodes.read or system.read can view the fleet summary."""
    try:
        enforce_permission(admin, "nodes", "read")
        return admin
    except PermissionDenied:
        pass
    try:
        enforce_permission(admin, "system", "read")
        return admin
    except PermissionDenied as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/summary", response_model=FleetSummaryResponse)
async def get_fleet_summary(
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_fleet_read),
):
    """Aggregate nodes, HPX tunnels, and HPX pulses for the fleet overview."""
    return await fleet_operator.get_summary(db, admin)
