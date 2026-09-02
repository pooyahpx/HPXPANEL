from fastapi import APIRouter, Depends, Query

from app.db import AsyncSession, get_db
from app.models.admin import AdminDetails
from app.models.observability import ObservabilitySummaryResponse, SystemStatsHistoryResponse
from app.operation import OperatorType
from app.operation.observability import ObservabilityOperation
from app.utils import responses

from .authentication import require_permission

router = APIRouter(tags=["Observability"], prefix="/api/observability", responses={401: responses._401})
observability_operator = ObservabilityOperation(operator_type=OperatorType.API)


@router.get("/summary", response_model=ObservabilitySummaryResponse)
async def get_observability_summary(
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("nodes", "stats")),
):
    """Unified NOC summary: per-node health, resources, protocols, and recent alerts."""
    return await observability_operator.get_summary(db, admin)


@router.get("/history", response_model=SystemStatsHistoryResponse)
async def get_observability_history(
    node_id: int | None = Query(default=None),
    hours: int = Query(default=24, ge=1, le=24 * 30),
    db: AsyncSession = Depends(get_db),
    _: AdminDetails = Depends(require_permission("nodes", "stats")),
):
    """Historical CPU/RAM/network charts for master or a specific node."""
    return await observability_operator.get_history(db, node_id=node_id, hours=hours)
