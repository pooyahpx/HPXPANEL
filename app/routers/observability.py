from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.db import AsyncSession, get_db
from app.models.admin import AdminDetails
from app.models.observability import (
    AlertEventStatus,
    ObservabilityAlertEventResponse,
    ObservabilityAlertEventUpdate,
    ObservabilitySummaryResponse,
    SystemStatsHistoryResponse,
)
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
    node_id: Annotated[int | None, Query()] = None,
    hours: Annotated[int, Query(ge=1, le=24 * 30)] = 24,
    db: AsyncSession = Depends(get_db),
    _: AdminDetails = Depends(require_permission("nodes", "stats")),
):
    """Historical CPU/RAM/network charts for master or a specific node."""
    return await observability_operator.get_history(db, node_id=node_id, hours=hours)


@router.get("/alerts", response_model=list[ObservabilityAlertEventResponse])
async def list_observability_alerts(
    status: Annotated[AlertEventStatus | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    db: AsyncSession = Depends(get_db),
    _: AdminDetails = Depends(require_permission("nodes", "stats")),
):
    """List observability alert events, optionally filtered by status."""
    return await observability_operator.list_alerts(db, status=status, limit=limit)


@router.patch("/alerts/{alert_id}", response_model=ObservabilityAlertEventResponse)
async def patch_observability_alert(
    alert_id: int,
    payload: ObservabilityAlertEventUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("nodes", "update")),
):
    """Acknowledge or resolve an observability alert event."""
    return await observability_operator.update_alert(db, admin, alert_id, payload)
