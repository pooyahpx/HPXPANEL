"""ICMP tunnel failover eligibility helpers (pure / lightly coupled)."""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta as td

FAILOVER_COOLDOWN = td(minutes=3)
FAILBACK_COOLDOWN = td(minutes=5)


def aware(value: dt | None) -> dt | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def can_attempt_failover(tunnel) -> tuple[bool, str | None]:
    if not getattr(tunnel, "auto_failover", False) or not getattr(tunnel, "backup_tunnel_id", None):
        return False, "failover disabled or no backup"
    if getattr(tunnel, "failover_active", False):
        return False, "already on backup path"
    last = aware(getattr(tunnel, "last_failover_at", None))
    if last and dt.now(UTC) - last < FAILOVER_COOLDOWN:
        return False, "failover cooldown"
    return True, None


def can_attempt_failback(tunnel) -> tuple[bool, str | None]:
    if not getattr(tunnel, "auto_failback", True) or not getattr(tunnel, "failover_active", False):
        return False, "failback disabled or not active"
    if not getattr(tunnel, "backup_tunnel_id", None):
        return False, "no backup"
    last = aware(getattr(tunnel, "last_failover_at", None))
    if last and dt.now(UTC) - last < FAILBACK_COOLDOWN:
        return False, "failback cooldown"
    return True, None
