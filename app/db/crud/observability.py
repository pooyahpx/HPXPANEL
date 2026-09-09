from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import NodeUserUsage, ObservabilityAlertEvent, ObservabilityAlertTimelineEvent, SystemStat, User
from app.models.observability import (
    AlertEventStatus,
    AlertTimelineEventType,
    ObservabilityAlertEventResponse,
    ObservabilityAlertTimelineEventResponse,
    SystemStatsHistoryPoint,
)
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


def _alert_event_to_response(
    event: ObservabilityAlertEvent,
    node_name: str | None = None,
    *,
    timeline: list | None = None,
) -> ObservabilityAlertEventResponse:
    from app.models.observability import AlertSeverity

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
        severity=AlertSeverity(event.severity or AlertSeverity.warning.value),
        assignee=event.assignee,
        acked_at=event.acked_at,
        acked_by=event.acked_by,
        resolved_at=event.resolved_at,
        resolved_by=event.resolved_by,
        note=event.note,
        created_at=event.created_at,
        timeline=timeline or [],
    )


def _timeline_to_response(row: ObservabilityAlertTimelineEvent) -> ObservabilityAlertTimelineEventResponse:
    return ObservabilityAlertTimelineEventResponse(
        id=row.id,
        alert_id=row.alert_id,
        created_at=row.created_at,
        actor=row.actor,
        event_type=AlertTimelineEventType(row.event_type),
        from_status=AlertEventStatus(row.from_status) if row.from_status else None,
        to_status=AlertEventStatus(row.to_status) if row.to_status else None,
        message=row.message,
        payload=row.payload,
    )


async def append_alert_timeline_event(
    db: AsyncSession,
    *,
    alert_id: int,
    event_type: str | AlertTimelineEventType,
    message: str,
    actor: str | None = None,
    from_status: str | None = None,
    to_status: str | None = None,
    payload: dict | None = None,
    commit: bool = False,
) -> ObservabilityAlertTimelineEvent:
    event_type_value = event_type.value if isinstance(event_type, AlertTimelineEventType) else event_type
    row = ObservabilityAlertTimelineEvent(
        alert_id=alert_id,
        actor=actor,
        event_type=event_type_value,
        from_status=from_status,
        to_status=to_status,
        message=message[:1000],
        payload=payload,
    )
    bind = await db.connection()
    if bind.dialect.name == "sqlite":
        next_id = (
            await db.execute(select(func.coalesce(func.max(ObservabilityAlertTimelineEvent.id), 0) + 1))
        ).scalar_one()
        row.id = int(next_id)
    db.add(row)
    if commit:
        await db.commit()
        await db.refresh(row)
    else:
        await db.flush()
    return row


async def list_alert_timeline_events(db: AsyncSession, alert_id: int) -> list[ObservabilityAlertTimelineEventResponse]:
    stmt = (
        select(ObservabilityAlertTimelineEvent)
        .where(ObservabilityAlertTimelineEvent.alert_id == alert_id)
        .order_by(ObservabilityAlertTimelineEvent.created_at.asc(), ObservabilityAlertTimelineEvent.id.asc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [_timeline_to_response(row) for row in rows]


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


async def get_alert_event_detail(db: AsyncSession, alert_id: int) -> ObservabilityAlertEventResponse | None:
    from app.db.models import Node

    stmt = (
        select(ObservabilityAlertEvent, Node.name)
        .outerjoin(Node, Node.id == ObservabilityAlertEvent.node_id)
        .where(ObservabilityAlertEvent.id == alert_id)
    )
    row = (await db.execute(stmt)).one_or_none()
    if row is None:
        return None
    event, node_name = row
    timeline = await list_alert_timeline_events(db, alert_id)
    return _alert_event_to_response(event, node_name, timeline=timeline)


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
    previous_status = event.status
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

    if previous_status != status_value:
        await append_alert_timeline_event(
            db,
            alert_id=event.id,
            event_type=AlertTimelineEventType.status_changed,
            actor=actor_username,
            from_status=previous_status,
            to_status=status_value,
            message=f"Status changed from {previous_status} to {status_value}",
        )
    if note:
        await append_alert_timeline_event(
            db,
            alert_id=event.id,
            event_type=AlertTimelineEventType.note_added,
            actor=actor_username,
            message=note,
        )

    await db.commit()
    await db.refresh(event)
    return event


async def add_alert_note(
    db: AsyncSession,
    alert_id: int,
    *,
    message: str,
    actor_username: str,
) -> ObservabilityAlertEvent | None:
    event = await get_alert_event(db, alert_id)
    if event is None:
        return None
    event.note = message[:500]
    await append_alert_timeline_event(
        db,
        alert_id=event.id,
        event_type=AlertTimelineEventType.note_added,
        actor=actor_username,
        message=message,
    )
    await db.commit()
    await db.refresh(event)
    return event


async def update_alert_severity(
    db: AsyncSession,
    alert_id: int,
    *,
    severity: str,
    actor_username: str,
) -> ObservabilityAlertEvent | None:
    event = await get_alert_event(db, alert_id)
    if event is None:
        return None
    previous = event.severity
    event.severity = severity
    await append_alert_timeline_event(
        db,
        alert_id=event.id,
        event_type=AlertTimelineEventType.severity_changed,
        actor=actor_username,
        message=f"Severity changed from {previous} to {severity}",
        payload={"from": previous, "to": severity},
    )
    await db.commit()
    await db.refresh(event)
    return event


async def update_alert_assignee(
    db: AsyncSession,
    alert_id: int,
    *,
    assignee: str | None,
    actor_username: str,
) -> ObservabilityAlertEvent | None:
    event = await get_alert_event(db, alert_id)
    if event is None:
        return None
    previous = event.assignee
    event.assignee = assignee
    label = assignee or "(unassigned)"
    await append_alert_timeline_event(
        db,
        alert_id=event.id,
        event_type=AlertTimelineEventType.assignee_changed,
        actor=actor_username,
        message=f"Assignee changed from {previous or '(none)'} to {label}",
        payload={"from": previous, "to": assignee},
    )
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
    severity: str = "warning",
) -> ObservabilityAlertEvent:
    event = ObservabilityAlertEvent(
        scope=scope,
        node_id=node_id,
        metric=metric,
        value=value,
        threshold=threshold,
        message=message,
        status=AlertEventStatus.open.value,
        severity=severity,
    )
    # Original alert_events migration used BIGINT PK; SQLite only autoincrements
    # INTEGER PRIMARY KEY, so assign the next id explicitly on sqlite.
    bind = await db.connection()
    if bind.dialect.name == "sqlite":
        next_id = (await db.execute(select(func.coalesce(func.max(ObservabilityAlertEvent.id), 0) + 1))).scalar_one()
        event.id = int(next_id)
    db.add(event)
    await db.flush()
    await append_alert_timeline_event(
        db,
        alert_id=event.id,
        event_type=AlertTimelineEventType.created,
        actor=None,
        to_status=AlertEventStatus.open.value,
        message=message,
        payload={"metric": metric, "value": value, "threshold": threshold},
    )
    await db.commit()
    await db.refresh(event)
    return event
