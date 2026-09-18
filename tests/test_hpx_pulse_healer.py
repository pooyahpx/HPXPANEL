"""P4 Pulse healer stale-agent watchdog and heal cooldown."""

from datetime import UTC, datetime as dt, timedelta as td
from types import SimpleNamespace

from app.db.models import HpxPulseStatus
from app.services.hpx_pulse.healer import (
    AGENT_STALE_SECONDS,
    HEAL_COOLDOWN,
    diagnose_pulse,
    evaluate_and_repair,
)


def _pulse(**kwargs):
    now = dt.now(UTC)
    defaults = {
        "name": "p1",
        "enabled": True,
        "status": HpxPulseStatus.running,
        "auto_heal_enabled": True,
        "iran_agent_key_hash": "iran",
        "abroad_agent_key_hash": "abroad",
        "iran_agent_last_seen": now,
        "abroad_agent_last_seen": now,
        "iran_agent_command": None,
        "abroad_agent_command": None,
        "last_heal_at": None,
        "last_heal_action": None,
        "heal_count_window": 0,
        "last_health_check": None,
        "last_status_change": now,
        "message": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_stale_agents_mark_unhealthy_and_queue_restart():
    stale = dt.now(UTC) - td(seconds=AGENT_STALE_SECONDS + 30)
    pulse = _pulse(iran_agent_last_seen=stale, abroad_agent_last_seen=stale)
    result = evaluate_and_repair(pulse, auto=True)
    assert result.marked_unhealthy or pulse.status == HpxPulseStatus.unhealthy
    assert result.repaired
    assert pulse.iran_agent_command == "restart"
    assert pulse.abroad_agent_command == "restart"
    assert pulse.last_heal_action


def test_heal_cooldown_skips():
    stale = dt.now(UTC) - td(seconds=AGENT_STALE_SECONDS + 30)
    pulse = _pulse(
        status=HpxPulseStatus.unhealthy,
        iran_agent_last_seen=stale,
        abroad_agent_last_seen=stale,
        last_heal_at=dt.now(UTC) - td(seconds=10),
        heal_count_window=1,
    )
    assert HEAL_COOLDOWN.total_seconds() > 10
    result = evaluate_and_repair(pulse, auto=True)
    assert result.skipped_reason == "cooldown active"
    assert not result.repaired


def test_diagnose_lists_stale_sides():
    stale = dt.now(UTC) - td(seconds=AGENT_STALE_SECONDS + 5)
    pulse = _pulse(iran_agent_last_seen=stale, abroad_agent_last_seen=dt.now(UTC))
    issues = diagnose_pulse(pulse)
    codes = {i.code for i in issues}
    assert "iran_agent_stale" in codes
    assert "abroad_agent_stale" not in codes
