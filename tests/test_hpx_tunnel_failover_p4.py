"""P4 ICMP failover eligibility helpers."""

from datetime import UTC, datetime as dt, timedelta as td
from types import SimpleNamespace

from app.services.hpx_tunnel.failover import can_attempt_failback, can_attempt_failover


def test_failover_requires_backup_and_flag():
    ok, reason = can_attempt_failover(SimpleNamespace(auto_failover=False, backup_tunnel_id=2, failover_active=False, last_failover_at=None))
    assert ok is False
    assert "disabled" in (reason or "")

    ok, _ = can_attempt_failover(SimpleNamespace(auto_failover=True, backup_tunnel_id=2, failover_active=False, last_failover_at=None))
    assert ok is True


def test_failover_cooldown():
    ok, reason = can_attempt_failover(
        SimpleNamespace(
            auto_failover=True,
            backup_tunnel_id=2,
            failover_active=False,
            last_failover_at=dt.now(UTC) - td(seconds=30),
        )
    )
    assert ok is False
    assert "cooldown" in (reason or "")


def test_failback_requires_active_failover():
    ok, _ = can_attempt_failback(
        SimpleNamespace(auto_failback=True, failover_active=False, backup_tunnel_id=2, last_failover_at=None)
    )
    assert ok is False

    ok, _ = can_attempt_failback(
        SimpleNamespace(
            auto_failback=True,
            failover_active=True,
            backup_tunnel_id=2,
            last_failover_at=dt.now(UTC) - td(minutes=10),
        )
    )
    assert ok is True
