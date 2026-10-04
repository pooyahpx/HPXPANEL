"""TCP-reverse autofix + Host linker for Pulse Diagnose agent."""

from types import SimpleNamespace

from app.services.hpx_pulse.config_linker import rewrite_host_addresses_to_iran, scan_hosts_for_pulse
from app.services.hpx_pulse.tcp_autofix import (
    EXTREME_STEALTH,
    EXTREME_TCP,
    diag_has_stall,
    should_autofix_tcp_extreme,
)


def test_scan_flags_abroad_host():
    hosts = [
        SimpleNamespace(id=1, remark="reality", port=443, address={"193.42.11.147"}),
        SimpleNamespace(id=2, remark="ok", port=443, address={"93.113.230.164"}),
    ]
    hits = scan_hosts_for_pulse(
        hosts, iran_ip="93.113.230.164", abroad_ip="193.42.11.147"
    )
    by_id = {h.host_id: h for h in hits}
    assert by_id[1].issue == "abroad_ip"
    assert by_id[2].issue == "ok_iran"


def test_rewrite_abroad_to_iran():
    out = rewrite_host_addresses_to_iran(
        {"193.42.11.147", "keep-other"},
        abroad_ip="193.42.11.147",
        iran_ip="93.113.230.164",
    )
    assert "93.113.230.164" in out
    assert "193.42.11.147" not in out
    assert "keep-other" in out


def test_should_upgrade_plain_stealth():
    pulse = SimpleNamespace(
        tunnel_mode="reverse_stealth",
        profile_id="pulse-reverse-tcp-stealth",
        diag_report=None,
    )
    assert should_autofix_tcp_extreme(pulse) == EXTREME_STEALTH


def test_should_upgrade_plain_tcp():
    pulse = SimpleNamespace(
        tunnel_mode="reverse_tcp",
        profile_id="pulse-reverse-tcp",
        diag_report=None,
    )
    assert should_autofix_tcp_extreme(pulse) == EXTREME_TCP


def test_no_upgrade_when_already_extreme():
    pulse = SimpleNamespace(
        tunnel_mode="reverse_stealth",
        profile_id=EXTREME_STEALTH,
        diag_report=None,
    )
    assert should_autofix_tcp_extreme(pulse) is None


def test_diag_has_stall():
    report = {
        "sides": {
            "abroad": {
                "tcp": {"forward_exchange": {"stall": True, "detail": "stall_after_connect"}},
            }
        }
    }
    assert diag_has_stall(report) is True
    assert diag_has_stall({"sides": {"abroad": {"tcp": {}}}}) is False
