from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel
from sqlalchemy import inspect as sa_inspect

from app.db import GetDB
from app.db.models import AuditLog
from app.utils.logger import get_logger

logger = get_logger("audit")

REDACTED = "[REDACTED]"
_SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "authorization",
    "credential",
    "secret",
    "token",
    "api_key",
    "apikey",
    "private_key",
    "join_key",
    "agent_key",
    "temp_key",
)
_INLINE_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(bearer|apikey)\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)\b(password|passwd|token|secret|api[_-]?key|authorization)\b(\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"\bpg_key_[0-9a-fA-F-]{20,}\b"),
)


def _is_sensitive_key(key: object) -> bool:
    snake_case = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(key))
    normalized = re.sub(r"[^a-z0-9]+", "_", snake_case.lower()).strip("_")
    segments = normalized.split("_")
    return "key" in segments or normalized == "keyhash" or any(
        part in normalized for part in _SENSITIVE_KEY_PARTS
    )


def redact_text(value: str) -> str:
    redacted = value
    for pattern in _INLINE_SECRET_PATTERNS:
        if pattern.groups >= 2:
            redacted = pattern.sub(lambda match: f"{match.group(1)}{match.group(2)}{REDACTED}", redacted)
        else:
            redacted = pattern.sub(REDACTED, redacted)
    return redacted


def redact(value: Any) -> Any:
    """Recursively convert a value to JSON-safe data and remove secret-like fields."""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return redact(value.value)
    if isinstance(value, BaseModel):
        return redact(value.model_dump(mode="json"))
    if isinstance(value, Mapping):
        return {
            str(key): REDACTED if _is_sensitive_key(key) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [redact(item) for item in sorted(value, key=str)]
    return redact_text(str(value))


def model_snapshot(instance: object | None) -> dict[str, Any] | None:
    """Serialize mapped columns only, deliberately excluding relationships."""
    if instance is None:
        return None
    mapper = sa_inspect(type(instance))
    values = {column.key: getattr(instance, column.key) for column in mapper.columns}
    return redact(values)


async def record_audit_log(
    *,
    action: str,
    resource: str,
    result: str,
    actor_id: int | None = None,
    actor_username: str | None = None,
    source_ip: str | None = None,
    resource_id: str | int | None = None,
    before: Any = None,
    after: Any = None,
    detail: str | None = None,
) -> None:
    """Persist an audit row in an independent transaction; never fail the primary operation."""
    try:
        async with GetDB() as db:
            db.add(
                AuditLog(
                    action=action[:64],
                    resource=resource[:64],
                    result=result[:16],
                    actor_id=actor_id,
                    actor_username=redact_text(actor_username)[:128] if actor_username else None,
                    source_ip=source_ip[:64] if source_ip else None,
                    resource_id=str(resource_id)[:256] if resource_id is not None else None,
                    before=redact(before),
                    after=redact(after),
                    detail=redact_text(detail) if detail else None,
                )
            )
            await db.commit()
    except Exception as exc:
        logger.warning("Unable to persist audit event %s.%s: %s", resource, action, type(exc).__name__)
