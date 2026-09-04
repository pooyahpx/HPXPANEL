from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import NodeUserUsage, ObservabilityAlertEvent, SystemStat, User
from app.models.observability import AlertEventStatus, ObservabilityAlertEventResponse, SystemStatsHistoryPoint
from app.models.stats import Period


async def get_online_users_by_node(db: AsyncSession, *, window_minutes: int = 2) -> dict[int, int]:
    since = datetime.now(UTC) - timedelta(minutes=window_minutes)
    stmt = (
        select(NodeUserUsage.node_id, func.count(func.distinct(NodeUserUsage.user_id)))
        .where(NodeUserUsage.created_at >= since, NodeUserUsage.node_id.isnot(None))
        .group_by(NodeUserUsage.node_id)
    )
    rows = await db.execute(stmt)
    return {int(node_id): int(count) for node_id, count in rows.all() if node_id is not None}


async def count_total_users(db: AsyncSession) -> int:
    return int((await db.execute(select(func.count(User.id)))).scalar_one() or 0)


async def insert_system_stat(db: AsyncSession, stat: SystemStat) -> None:
    db.add(stat)
    await db.commit()


async def purge_old_node_stats(db: AsyncSession, *, retention_days: int) -> int:
    if retention_days <= 0:
        return 0
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    from app.db.models import NodeStat

    result = await db.execute(delete(NodeStat).where(NodeStat.created_at < cutoff))
    await db.commit()
    return int(result.rowcount or 0)


async def purge_old_system_stats(db: AsyncSession, *, retention_days: int) -> int:
    if retention_days <= 0:
        return 0
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    result = await db.execute(delete(SystemStat).where(SystemStat.created_at < cutoff))
    await db.commit()
    return int(result.rowcount or 0)


async def get_system_stats_history(
    db: AsyncSession,
    *,
    node_id: int | None,
    start: datetime,
    end: datetime,
    period: Period = Period.hour,
) -> list[SystemStatsHistoryPoint]:
    from app.db.crud.general import _build_trunc_expression
    from app.db.models import NodeStat

    if node_id is not None:
        table = NodeStat
        conditions = [NodeStat.node_id == node_id, NodeStat.created_at >= start, NodeStat.created_at <= end]
        mem_expr = func.avg((NodeStat.mem_used * 100.0) / func.nullif(NodeStat.mem_total, 0))
        cpu_expr = func.avg(NodeStat.cpu_usage)
        in_expr = func.avg(NodeStat.incoming_bandwidth_speed)
        out_expr = func.avg(NodeStat.outgoing_bandwidth_speed)
    else:
        table = SystemStat
        conditions = [SystemStat.created_at >= start, SystemStat.created_at <= end]
        mem_expr = func.avg((SystemStat.mem_used * 100.0) / func.nullif(SystemStat.mem_total, 0))
        cpu_expr = func.avg(SystemStat.cpu_usage)
        in_expr = func.avg(SystemStat.incoming_bandwidth_speed)
        out_expr = func.avg(SystemStat.outgoing_bandwidth_speed)

    trunc_expr = _build_trunc_expression(db, table.created_at, period, start.tzinfo)
    stmt = (
        select(
            trunc_expr.label("period_start"),
            mem_expr.label("mem_usage_percentage"),
            cpu_expr.label("cpu_usage_percentage"),
            in_expr.label("incoming_bandwidth_speed"),
            out_expr.label("outgoing_bandwidth_speed"),
        )
        .where(*conditions)
        .group_by(trunc_expr)
        .order_by(trunc_expr)
    )
    rows = await db.execute(stmt)
    points: list[SystemStatsHistoryPoint] = []
    for row in rows.mappings():
        period_start = row["period_start"]
        if period_start.tzinfo is None:
            period_start = period_start.replace(tzinfo=UTC)
        points.append(
            SystemStatsHistoryPoint(
                period_start=period_start,
                cpu_usage_percentage=float(row["cpu_usage_percentage"] or 0),
                mem_usage_percentage=float(row["mem_usage_percentage"] or 0),
                incoming_mbps=float(row["incoming_bandwidth_speed"] or 0) / 1_000_000,
                outgoing_mbps=float(row["outgoing_bandwidth_speed"] or 0) / 1_000_000,
            )
        )
    return points


def _alert_event_to_response(event: ObservabilityAlertEvent, node_name: str | None = None) -> ObservabilityAlertEventResponse:
    return ObservabilityAlertEventResponse(
        id=event.id,
        scope=event.scope,
        node_id=event.node_id,
        node_name=node_name,
        metric=event.metric,
        value=event.value,
        threshold=event.threshold,
        message=event.message,
        status=AlertEventStatus(event.status),
        acked_at=event.acked_at,
        acked_by=event.acked_by,
        resolved_at=event.resolved_at,
        resolved_by=event.resolved_by,
        note=event.note,
        created_at=event.created_at,
    )


async def list_alert_events(
    db: AsyncSession,
    *,
    status: str | AlertEventStatus | None = None,
    limit: int = 50,
) -> list[ObservabilityAlertEventResponse]:
    from app.db.models import Node

    stmt = (
        select(ObservabilityAlertEvent, Node.name)
        .outerjoin(Node, Node.id == ObservabilityAlertEvent.node_id)
        .order_by(ObservabilityAlertEvent.created_at.desc())
        .limit(limit)
    )
    if status is not None:
        status_value = status.value if isinstance(status, AlertEventStatus) else status
        stmt = stmt.where(ObservabilityAlertEvent.status == status_value)
    rows = await db.execute(stmt)
    return [_alert_event_to_response(event, node_name) for event, node_name in rows.all()]


async def get_recent_alert_events(db: AsyncSession, *, limit: int = 20) -> list[ObservabilityAlertEventResponse]:
    return await list_alert_events(db, limit=limit)


async def get_alert_event(db: AsyncSession, alert_id: int) -> ObservabilityAlertEvent | None:
    return await db.get(ObservabilityAlertEvent, alert_id)


async def update_alert_event_status(
    db: AsyncSession,
    alert_id: int,
    *,
    status: str | AlertEventStatus,
    note: str | None,
    actor_username: str,
) -> ObservabilityAlertEvent | None:
    event = await get_alert_event(db, alert_id)
    if event is None:
        return None

    status_value = status.value if isinstance(status, AlertEventStatus) else status
    now = datetime.now(UTC)
    event.status = status_value
    if note is not None:
        event.note = note

    if status_value == AlertEventStatus.acked.value:
        event.acked_at = now
        event.acked_by = actor_username
    elif status_value == AlertEventStatus.resolved.value:
        event.resolved_at = now
        event.resolved_by = actor_username
        if event.acked_at is None:
            event.acked_at = now
            event.acked_by = actor_username
    elif status_value == AlertEventStatus.open.value:
        event.acked_at = None
        event.acked_by = None
        event.resolved_at = None
        event.resolved_by = None

    await db.commit()
    await db.refresh(event)
    return event


async def has_recent_alert(
    db: AsyncSession,
    *,
    scope: str,
    metric: str,
    node_id: int | None,
    minutes: int,
) -> bool:
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)
    stmt = select(ObservabilityAlertEvent.id).where(
        ObservabilityAlertEvent.scope == scope,
        ObservabilityAlertEvent.metric == metric,
        ObservabilityAlertEvent.created_at >= cutoff,
    )
    if node_id is None:
        stmt = stmt.where(ObservabilityAlertEvent.node_id.is_(None))
    else:
        stmt = stmt.where(ObservabilityAlertEvent.node_id == node_id)
    return (await db.execute(stmt.limit(1))).scalar_one_or_none() is not None


async def record_alert_event(
    db: AsyncSession,
    *,
    scope: str,
    metric: str,
    value: float,
    threshold: float,
    message: str,
    node_id: int | None = None,
) -> ObservabilityAlertEvent:
    event = ObservabilityAlertEvent(
        scope=scope,
        node_id=node_id,
        metric=metric,
        value=value,
        threshold=threshold,
        message=message,
        status=AlertEventStatus.open.value,
    )
    # Original alert_events migration used BIGINT PK; SQLite only autoincrements
    # INTEGER PRIMARY KEY, so assign the next id explicitly on sqlite.
    bind = await db.connection()
    if bind.dialect.name == "sqlite":
        next_id = (
            await db.execute(select(func.coalesce(func.max(ObservabilityAlertEvent.id), 0) + 1))
        ).scalar_one()
        event.id = int(next_id)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event
