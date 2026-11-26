"""Mother-config consumption / eligibility / online stats for the admin UI."""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserStatus
from app.models.settings import ExternalConfig, Subscription

_ONLINE_WINDOW = timedelta(minutes=2)


class MotherConfigItemUsage(BaseModel):
    name: str = ""
    enabled: bool = True
    respect_user_quota: bool = True
    personalize: bool = True
    eligible_users: int = 0
    gated_by_quota: int = 0
    gated_by_status: int = 0
    online_users: int = 0


class MotherConfigUsageResponse(BaseModel):
    total_users: int = 0
    active_users: int = 0
    on_hold_users: int = 0
    limited_users: int = 0
    expired_users: int = 0
    disabled_users: int = 0
    # Users who can receive at least one quota-gated mother config
    eligible_for_quota_gated: int = 0
    # Active/on_hold but volume exhausted
    exhausted_volume: int = 0
    # Unlimited accounts (data_limit null/0) among active/on_hold
    unlimited_users: int = 0
    # Eligible users with online_at inside the last 2 minutes
    online_users: int = 0
    used_traffic_bytes: int = 0
    data_limit_bytes: int = 0
    remaining_bytes: int = 0
    usage_pct: float = Field(default=0.0, description="0–100 across limited eligible users")
    configs: list[MotherConfigItemUsage] = Field(default_factory=list)
    enabled_configs: int = 0
    total_configs: int = 0
    personalized_configs: int = 0


def _fmt_status(status: UserStatus | str | None) -> str:
    if status is None:
        return ""
    return status.value if hasattr(status, "value") else str(status)


def _is_online(online_at, *, now: dt) -> bool:
    if online_at is None:
        return False
    ts = online_at if online_at.tzinfo else online_at.replace(tzinfo=UTC)
    return ts >= now - _ONLINE_WINDOW


async def compute_mother_config_usage(
    db: AsyncSession, subscription: Subscription | None
) -> MotherConfigUsageResponse:
    """Aggregate panel-side consumption for mother / external configs."""
    configs = list(getattr(subscription, "external_configs", None) or [])
    rows = (await db.execute(select(User.status, User.data_limit, User.used_traffic, User.online_at))).all()
    now = dt.now(UTC)

    total = len(rows)
    by_status = {"active": 0, "on_hold": 0, "limited": 0, "expired": 0, "disabled": 0}
    eligible = 0
    exhausted = 0
    unlimited = 0
    online_eligible = 0
    used_sum = 0
    limit_sum = 0
    remaining_sum = 0
    limited_used = 0
    limited_cap = 0

    for status, data_limit, used_traffic, online_at in rows:
        st = _fmt_status(status)
        if st in by_status:
            by_status[st] += 1
        used = int(used_traffic or 0)
        limit = int(data_limit) if data_limit is not None else 0
        used_sum += used
        if limit > 0:
            limit_sum += limit

        is_receivable_status = st in {"active", "on_hold"}
        has_quota = limit <= 0 or used < limit
        if limit <= 0 and is_receivable_status:
            unlimited += 1
        if is_receivable_status and has_quota:
            eligible += 1
            if _is_online(online_at, now=now):
                online_eligible += 1
            if limit > 0:
                limited_used += used
                limited_cap += limit
                remaining_sum += max(limit - used, 0)
        elif is_receivable_status and not has_quota:
            exhausted += 1

    usage_pct = round((100.0 * limited_used / limited_cap), 1) if limited_cap > 0 else 0.0

    gated_by_status = total - by_status["active"] - by_status["on_hold"]
    status_only_eligible = by_status["active"] + by_status["on_hold"]
    status_only_online = 0
    for status, _dl, _ut, online_at in rows:
        st = _fmt_status(status)
        if st in {"active", "on_hold"} and _is_online(online_at, now=now):
            status_only_online += 1

    item_usages: list[MotherConfigItemUsage] = []
    for item in configs:
        if isinstance(item, ExternalConfig):
            name = item.name or ""
            enabled = bool(item.enabled)
            respect = bool(item.respect_user_quota)
            personalize = bool(item.personalize)
        elif isinstance(item, dict):
            name = str(item.get("name") or "")
            enabled = bool(item.get("enabled", True))
            respect = bool(item.get("respect_user_quota", True))
            personalize = bool(item.get("personalize", True))
        else:
            name = str(getattr(item, "name", "") or "")
            enabled = bool(getattr(item, "enabled", True))
            respect = bool(getattr(item, "respect_user_quota", True))
            personalize = bool(getattr(item, "personalize", True))

        # Non-personalized shared UUID always volume-gates
        effective_respect = True if not personalize else respect

        if not enabled:
            item_usages.append(
                MotherConfigItemUsage(
                    name=name,
                    enabled=False,
                    respect_user_quota=effective_respect,
                    personalize=personalize,
                    eligible_users=0,
                    gated_by_quota=0,
                    gated_by_status=gated_by_status,
                    online_users=0,
                )
            )
            continue

        if effective_respect:
            item_usages.append(
                MotherConfigItemUsage(
                    name=name,
                    enabled=True,
                    respect_user_quota=True,
                    personalize=personalize,
                    eligible_users=eligible,
                    gated_by_quota=exhausted,
                    gated_by_status=gated_by_status,
                    online_users=online_eligible,
                )
            )
        else:
            item_usages.append(
                MotherConfigItemUsage(
                    name=name,
                    enabled=True,
                    respect_user_quota=False,
                    personalize=personalize,
                    eligible_users=status_only_eligible,
                    gated_by_quota=0,
                    gated_by_status=gated_by_status,
                    online_users=status_only_online,
                )
            )

    return MotherConfigUsageResponse(
        total_users=total,
        active_users=by_status["active"],
        on_hold_users=by_status["on_hold"],
        limited_users=by_status["limited"],
        expired_users=by_status["expired"],
        disabled_users=by_status["disabled"],
        eligible_for_quota_gated=eligible,
        exhausted_volume=exhausted,
        unlimited_users=unlimited,
        online_users=online_eligible,
        used_traffic_bytes=int(used_sum),
        data_limit_bytes=int(limit_sum),
        remaining_bytes=int(remaining_sum),
        usage_pct=usage_pct,
        configs=item_usages,
        enabled_configs=sum(1 for c in item_usages if c.enabled),
        total_configs=len(item_usages),
        personalized_configs=sum(1 for c in item_usages if c.enabled and c.personalize),
    )
