"""Helpers for per-admin prepaid create budget (toman)."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Any

BYTES_PER_GB = 1024**3


def data_limit_to_billable_gb(data_limit: int | None) -> int:
    """Whole GBs charged for a data limit. Unlimited (0/None) → 0 GB charge."""
    if data_limit is None or data_limit <= 0:
        return 0
    return max(1, math.ceil(data_limit / BYTES_PER_GB))


def expire_to_billable_days(
    *,
    expire: datetime | None = None,
    on_hold_expire_duration: float | None = None,
    now: datetime | None = None,
) -> int:
    """Whole days charged for expiry. Unlimited → 0."""
    if on_hold_expire_duration is not None:
        seconds = int(on_hold_expire_duration)
        if seconds <= 0:
            return 0
        return max(1, math.ceil(seconds / 86_400))

    if expire is None:
        return 0

    if expire.tzinfo is None:
        expire = expire.replace(tzinfo=UTC)
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)

    delta = expire - current
    if delta.total_seconds() <= 0:
        return 0
    return max(1, math.ceil(delta.total_seconds() / 86_400))


def calculate_create_budget_cost(
    *,
    data_limit: int | None,
    expire: datetime | None = None,
    on_hold_expire_duration: float | None = None,
    price_per_gb: int,
    price_per_day: int,
    now: datetime | None = None,
) -> int:
    """Cost in toman for creating a user under budget rules."""
    gb = data_limit_to_billable_gb(data_limit)
    days = expire_to_billable_days(expire=expire, on_hold_expire_duration=on_hold_expire_duration, now=now)
    per_gb = max(0, int(price_per_gb or 0))
    per_day = max(0, int(price_per_day or 0))
    return gb * per_gb + days * per_day


def cost_from_user_payload(payload: Any, *, price_per_gb: int, price_per_day: int) -> int:
    """Compute cost from a UserCreate-like object."""
    status = getattr(payload, "status", None)
    status_value = getattr(status, "value", status)
    on_hold_duration = None
    expire = getattr(payload, "expire", None)
    if status_value == "on_hold":
        on_hold_duration = getattr(payload, "on_hold_expire_duration", None)
        expire = None
    return calculate_create_budget_cost(
        data_limit=getattr(payload, "data_limit", None),
        expire=expire,
        on_hold_expire_duration=on_hold_duration,
        price_per_gb=price_per_gb,
        price_per_day=price_per_day,
    )


def duration_days_to_expire(days: int, *, now: datetime | None = None) -> datetime | None:
    if not days:
        return None
    current = now or datetime.now(UTC)
    return current + timedelta(days=days)
