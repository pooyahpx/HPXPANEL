"""Helpers for per-admin prepaid create budget (toman)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

BYTES_PER_GB = 1024**3


@dataclass(frozen=True)
class CreateBudgetQuote:
    gb: int
    days: int
    amount: int
    pricing_mode: str  # linear | tier
    tier_gb: int | None
    data_cost: int
    days_cost: int


def data_limit_to_billable_gb(data_limit: int | None) -> int:
    """Whole GBs charged for a data limit. Unlimited (0/None) → 0 GB charge."""
    if data_limit is None or data_limit <= 0:
        return 0
    return max(1, math.ceil(data_limit / BYTES_PER_GB))


def _as_aware_datetime(value: Any, *, now: datetime | None = None) -> datetime | None:
    """Accept datetime / unix seconds / ms; treat <=0 as unlimited."""
    if value is None:
        return None
    if isinstance(value, datetime):
        expire = value
    elif isinstance(value, (int, float)):
        ts = float(value)
        if ts <= 0:
            return None
        # Heuristic: values that look like milliseconds
        if ts > 10_000_000_000:
            ts = ts / 1000.0
        expire = datetime.fromtimestamp(ts, tz=UTC)
    else:
        return None

    if expire.tzinfo is None:
        expire = expire.replace(tzinfo=UTC)
    return expire


def expire_to_billable_days(
    *,
    expire: Any = None,
    on_hold_expire_duration: float | None = None,
    now: datetime | None = None,
) -> int:
    """Whole days charged for expiry. Unlimited → 0.

    Accepts datetime or unix timestamp for expire. Duration (seconds) is preferred
    when provided (>0); otherwise expire datetime is used.
    """
    if on_hold_expire_duration is not None:
        try:
            seconds = int(on_hold_expire_duration)
        except (TypeError, ValueError):
            seconds = 0
        if seconds > 0:
            return max(1, math.ceil(seconds / 86_400))

    expire_dt = _as_aware_datetime(expire, now=now)
    if expire_dt is None:
        return 0

    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)

    delta = expire_dt - current
    if delta.total_seconds() <= 0:
        return 0
    return max(1, math.ceil(delta.total_seconds() / 86_400))


def normalize_price_tiers(raw: Any) -> list[dict[str, int | None]]:
    """Normalize [{gb, price_toman, days?}] tiers; invalid rows dropped."""
    if not raw:
        return []
    if not isinstance(raw, list):
        return []
    out: list[dict[str, int | None]] = []
    seen: set[tuple[int, int | None]] = set()
    for item in raw:
        if hasattr(item, "model_dump"):
            item = item.model_dump()
        if not isinstance(item, dict):
            continue
        try:
            gb = int(item.get("gb") or 0)
            price = int(item.get("price_toman") or 0)
        except (TypeError, ValueError):
            continue
        if gb <= 0 or price < 0:
            continue
        days_raw = item.get("days", None)
        days: int | None
        if days_raw is None or days_raw == "" or days_raw == 0:
            days = None
        else:
            try:
                days = int(days_raw)
            except (TypeError, ValueError):
                continue
            if days < 0:
                continue
            if days == 0:
                days = None
        key = (gb, days)
        if key in seen:
            continue
        seen.add(key)
        out.append({"gb": gb, "price_toman": price, "days": days})
    out.sort(key=lambda t: (int(t["gb"] or 0), int(t["days"] or 0)))
    return out


def calculate_create_budget_cost(
    *,
    data_limit: int | None,
    expire: Any = None,
    on_hold_expire_duration: float | None = None,
    price_per_gb: int,
    price_per_day: int,
    tiers: Any = None,
    now: datetime | None = None,
) -> CreateBudgetQuote:
    """Cost in toman for creating a user under budget rules (linear or custom GB tier)."""
    gb = data_limit_to_billable_gb(data_limit)
    days = expire_to_billable_days(expire=expire, on_hold_expire_duration=on_hold_expire_duration, now=now)
    per_gb = max(0, int(price_per_gb or 0))
    per_day = max(0, int(price_per_day or 0))
    normalized = normalize_price_tiers(tiers)

    # Prefer exact package match (gb+days), then gb-only tier.
    package_match = None
    gb_only_match = None
    for tier in normalized:
        if int(tier["gb"] or 0) != gb:
            continue
        tier_days = tier.get("days")
        if tier_days is not None and int(tier_days) == days:
            package_match = tier
            break
        if tier_days is None and gb_only_match is None:
            gb_only_match = tier

    if package_match is not None:
        amount = int(package_match["price_toman"] or 0)
        return CreateBudgetQuote(
            gb=gb,
            days=days,
            amount=amount,
            pricing_mode="tier",
            tier_gb=gb,
            data_cost=amount,
            days_cost=0,
        )

    if gb_only_match is not None:
        data_cost = int(gb_only_match["price_toman"] or 0)
        days_cost = days * per_day
        return CreateBudgetQuote(
            gb=gb,
            days=days,
            amount=data_cost + days_cost,
            pricing_mode="tier",
            tier_gb=gb,
            data_cost=data_cost,
            days_cost=days_cost,
        )

    data_cost = gb * per_gb
    days_cost = days * per_day
    return CreateBudgetQuote(
        gb=gb,
        days=days,
        amount=data_cost + days_cost,
        pricing_mode="linear",
        tier_gb=None,
        data_cost=data_cost,
        days_cost=days_cost,
    )


def quote_from_user_payload(
    payload: Any,
    *,
    price_per_gb: int,
    price_per_day: int,
    tiers: Any = None,
    now: datetime | None = None,
) -> CreateBudgetQuote:
    """Compute quote from a UserCreate-like object in any status/expire shape."""
    status = getattr(payload, "status", None)
    status_value = getattr(status, "value", status)
    expire = getattr(payload, "expire", None)
    on_hold_duration = getattr(payload, "on_hold_expire_duration", None)

    # Prefer the field that matches status, but fall back so either mode still bills.
    if status_value == "on_hold":
        if on_hold_duration is None or int(on_hold_duration or 0) <= 0:
            # Fall back to absolute expire if duration missing
            pass
        else:
            expire = None
    else:
        # Active/other: use expire; if missing, still honor on_hold duration if present
        if expire is None or expire == 0:
            pass
        else:
            on_hold_duration = None

    return calculate_create_budget_cost(
        data_limit=getattr(payload, "data_limit", None),
        expire=expire,
        on_hold_expire_duration=on_hold_duration,
        price_per_gb=price_per_gb,
        price_per_day=price_per_day,
        tiers=tiers,
        now=now,
    )


def cost_from_user_payload(payload: Any, *, price_per_gb: int, price_per_day: int, tiers: Any = None) -> int:
    """Backward-compatible total cost helper."""
    return quote_from_user_payload(
        payload,
        price_per_gb=price_per_gb,
        price_per_day=price_per_day,
        tiers=tiers,
    ).amount


def budget_snapshot_from_db_user(db_user: Any) -> Any:
    """Minimal payload for quoting an existing DB user."""
    from types import SimpleNamespace

    return SimpleNamespace(
        status=getattr(db_user, "status", None),
        data_limit=getattr(db_user, "data_limit", None),
        expire=getattr(db_user, "expire", None),
        on_hold_expire_duration=getattr(db_user, "on_hold_expire_duration", None),
    )


def budget_snapshot_after_modify(db_user: Any, modified_user: Any) -> Any:
    """Effective user fields after applying a partial UserModify."""
    from types import SimpleNamespace

    fields = getattr(modified_user, "model_fields_set", None) or set()
    status = (
        modified_user.status
        if "status" in fields and getattr(modified_user, "status", None) is not None
        else getattr(db_user, "status", None)
    )
    data_limit = modified_user.data_limit if "data_limit" in fields else getattr(db_user, "data_limit", None)
    expire = modified_user.expire if "expire" in fields else getattr(db_user, "expire", None)
    on_hold = (
        modified_user.on_hold_expire_duration
        if "on_hold_expire_duration" in fields
        else getattr(db_user, "on_hold_expire_duration", None)
    )
    return SimpleNamespace(
        status=status,
        data_limit=data_limit,
        expire=expire,
        on_hold_expire_duration=on_hold,
    )


def quote_delta_from_payloads(
    old_payload: Any,
    new_payload: Any,
    *,
    price_per_gb: int,
    price_per_day: int,
    tiers: Any = None,
    now: datetime | None = None,
) -> CreateBudgetQuote:
    """Charge-only-on-increase: max(0, new_quote - old_quote). No refund on decrease."""
    current = now or datetime.now(UTC)
    old_q = quote_from_user_payload(
        old_payload,
        price_per_gb=price_per_gb,
        price_per_day=price_per_day,
        tiers=tiers,
        now=current,
    )
    new_q = quote_from_user_payload(
        new_payload,
        price_per_gb=price_per_gb,
        price_per_day=price_per_day,
        tiers=tiers,
        now=current,
    )
    amount = max(0, int(new_q.amount) - int(old_q.amount))
    if amount <= 0:
        return CreateBudgetQuote(
            gb=0,
            days=0,
            amount=0,
            pricing_mode="linear",
            tier_gb=None,
            data_cost=0,
            days_cost=0,
        )
    return CreateBudgetQuote(
        gb=max(0, int(new_q.gb) - int(old_q.gb)),
        days=max(0, int(new_q.days) - int(old_q.days)),
        amount=amount,
        pricing_mode=new_q.pricing_mode,
        tier_gb=new_q.tier_gb,
        data_cost=max(0, int(new_q.data_cost) - int(old_q.data_cost)),
        days_cost=max(0, int(new_q.days_cost) - int(old_q.days_cost)),
    )


def duration_days_to_expire(days: int, *, now: datetime | None = None) -> datetime | None:
    if not days:
        return None
    current = now or datetime.now(UTC)
    return current + timedelta(days=days)
