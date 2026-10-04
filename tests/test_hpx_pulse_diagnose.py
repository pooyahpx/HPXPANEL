"""Panel-side Pulse diagnose checklist."""

from types import SimpleNamespace
from datetime import UTC, datetime as dt, timedelta as td

from app.db.models import HpxPulseStatus
from app.services.hpx_pulse.diagnose import diagnose_pulse_record, diagnose_summary


def _pulse(**kwargs):
    now = dt.now(UTC)
    defaults = {
        "name": "p1",
        "status": HpxPulseStatus.unhealthy,
        "message": "cannot reach Iran tunnel/control — check Iran IP/firewall",
        "tunnel_mode": "reverse_stealth",
        "preset": "balance",
        "carrier": "stealth",
        "iran_public_ip": "1.1.1.1",
        "abroad_public_ip": "2.2.2.2",
        "control_port": 50008,
        "port_forwards": ["443=127.0.0.1:443"],
        "iran_agent_key_hash": "iran",
        "abroad_agent_key_hash": "abroad",
        "iran_agent_host": "ir",
        "abroad_agent_host": "ab",
        "iran_agent_last_seen": now,
        "abroad_agent_last_seen": now,
        "latency_ms": None,
        "auto_heal_enabled": True,
        "last_heal_action": None,
        "diag_report": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_diagnose_flags_missing_ping_on_reverse():
    checks = diagnose_pulse_record(_pulse())
    summary = diagnose_summary(checks)
    assert summary["fail"] >= 1
    assert any(c.name == "Live ping" and c.level == "fail" for c in checks)
    assert "firewall" in summary["primary_fix"].lower() or "Iran" in summary["primary_fix"]


def test_diagnose_ok_when_running_with_ping():
    checks = diagnose_pulse_record(
        _pulse(status=HpxPulseStatus.running, message="user path OK (Iran:443)", latency_ms=82.0)
    )
    summary = diagnose_summary(checks)
    assert summary["fail"] == 0
    assert summary["healthy"] is True


def test_diagnose_stale_agent():
    stale = dt.now(UTC) - td(seconds=600)
    checks = diagnose_pulse_record(_pulse(iran_agent_last_seen=stale, latency_ms=50.0, status=HpxPulseStatus.running))
    assert any(c.name == "Iran agent" and c.level == "fail" for c in checks)


def test_diagnose_agent_stall_after_connect():
    import time

    report = {
        "ts": time.time(),
        "sides": {
            "abroad": {
                "side": "abroad",
                "host": "ab",
                "engine_version": "1.8.5",
                "ts": time.time(),
                "mss": {"ok": True, "detail": "mss=1280"},
                "tcp": {
                    "control": {"ok": True, "state": "ok", "ms": 40.0, "detail": "connect ok"},
                    "forward": {"ok": True, "state": "ok", "ms": 42.0, "detail": "connect ok"},
                    "forward_exchange": {
                        "ok": False,
                        "state": "fail",
                        "stall": True,
                        "ms": 42.0,
                        "detail": "stall_after_connect: TCP connected but no bytes",
                        "fix": "Lower mss to 1200",
                    },
                },
                "verdict": {
                    "level": "fail",
                    "summary": "stall_after_connect: TCP connected but no bytes",
                    "fix": "Lower mss to 1200",
                },
            }
        },
    }
    checks = diagnose_pulse_record(
        _pulse(status=HpxPulseStatus.running, latency_ms=42.0, message="stall", diag_report=report)
    )
    stall = next(c for c in checks if c.name == "TCP data after connect (MSS test)")
    assert stall.level == "fail"
    assert "TCP Extreme" in stall.fix
    assert "Diagnose" in stall.fix or "Sync" in stall.fix

