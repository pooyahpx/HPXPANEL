import csv
import io
import json
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import func, or_, select

from app.db import AsyncSession, get_db
from app.db.models import AuditLog
from app.models.admin import AdminDetails
from app.models.audit import AuditLogQuery, AuditLogResponse, AuditLogsResponse
from app.utils import responses

from .authentication import require_permission

router = APIRouter(
    tags=["Audit Logs"],
    prefix="/api/audit",
    responses={401: responses._401, 403: responses._403},
)


def _filters(query: AuditLogQuery):
    filters = []
    if query.search:
        term = f"%{query.search}%"
        filters.append(
            or_(
                AuditLog.actor_username.ilike(term),
                AuditLog.action.ilike(term),
                AuditLog.resource.ilike(term),
                AuditLog.resource_id.ilike(term),
                AuditLog.detail.ilike(term),
            )
        )
    if query.actor:
        actor_term = f"%{query.actor}%"
        actor_filter = AuditLog.actor_username.ilike(actor_term)
        if query.actor.isdigit():
            actor_filter = or_(actor_filter, AuditLog.actor_id == int(query.actor))
        filters.append(actor_filter)
    if query.action:
        filters.append(AuditLog.action == query.action)
    if query.resource:
        filters.append(AuditLog.resource == query.resource)
    if query.result:
        filters.append(AuditLog.result == query.result)
    if query.start:
        filters.append(AuditLog.created_at >= query.start)
    if query.end:
        filters.append(AuditLog.created_at <= query.end)
    return filters


@router.get("", response_model=AuditLogsResponse)
async def list_audit_logs(
    query: Annotated[AuditLogQuery, Depends()],
    db: AsyncSession = Depends(get_db),
    _: AdminDetails = Depends(require_permission("audit_logs", "read")),
):
    filters = _filters(query)
    total = (await db.execute(select(func.count(AuditLog.id)).where(*filters))).scalar_one()
    logs = (
        (
            await db.execute(
                select(AuditLog)
                .where(*filters)
                .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
                .offset(query.offset)
                .limit(query.limit)
            )
        )
        .scalars()
        .all()
    )
    return AuditLogsResponse(logs=list(logs), total=total, offset=query.offset, limit=query.limit)


def _safe_csv_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    elif isinstance(value, datetime):
        text = value.isoformat()
    else:
        text = str(value)
    if text.startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text


@router.get("/export")
async def export_audit_logs(
    query: Annotated[AuditLogQuery, Depends()],
    db: AsyncSession = Depends(get_db),
    _: AdminDetails = Depends(require_permission("audit_logs", "read")),
):
    logs = (
        (
            await db.execute(
                select(AuditLog)
                .where(*_filters(query))
                .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
                .limit(10_000)
            )
        )
        .scalars()
        .all()
    )
    output = io.StringIO(newline="")
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    columns = (
        "id",
        "created_at",
        "actor_id",
        "actor_username",
        "source_ip",
        "action",
        "resource",
        "resource_id",
        "result",
        "detail",
        "before",
        "after",
    )
    writer.writerow(columns)
    for log in logs:
        writer.writerow(_safe_csv_cell(getattr(log, column)) for column in columns)
    filename = f"audit-logs-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.csv"
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{audit_id}", response_model=AuditLogResponse, responses={404: responses._404})
async def get_audit_log(
    audit_id: int,
    db: AsyncSession = Depends(get_db),
    _: AdminDetails = Depends(require_permission("audit_logs", "read")),
):
    log = (await db.execute(select(AuditLog).where(AuditLog.id == audit_id))).scalar_one_or_none()
    if log is None:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return log
