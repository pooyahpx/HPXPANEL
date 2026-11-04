"""Direct Spoof — advisor isolation, TOML render, reverse refusal."""

from types import SimpleNamespace

import pytest

from app.models.hpx_pulse import PulseAdviseRequest
from app.services.hpx_pulse.advisor import (
    assert_spoof_direct_only,
    advise,
    default_spoof_config,
    profile_meta,
)
from app.services.hpx_pulse.tunnel_render import render_for_side


def _spoof_pulse(**kwargs):
    defaults = {
        "tunnel_mode": "direct_l3",
        "carrier": "spoof",
        "preset": "balance",
        "profile_id": "pulse-direct-spoof-udp",
        "control_port": 45000,
        "iran_public_ip": "1.2.3.4",
        "abroad_public_ip": "5.6.7.8",
        "port_forwards": ["443"],
        "domain": None,
        "spoof_config": {
            "profile": "udp",
            "stealth": False,
            "src_ip": "",
            "src_pool": [],
            "mtu": 0,
            "sockbuf": 0,
            "icmp_reply": False,
        },
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_spoof_intent_ranks_direct_spoof_first():
    res = advise(PulseAdviseRequest(goal="spoof", cpu_cores=2, ram_mb=2048))
    assert res.profiles[0].profile_id.startswith("pulse-direct-spoof")
    assert res.profiles[0].carrier == "spoof"
    assert res.profiles[0].tunnel_mode == "direct_l3"
    top_ids = {p.profile_id for p in res.profiles[:3]}
    assert top_ids <= {
        "pulse-direct-spoof-udp",
        "pulse-direct-spoof-icmp",
        "pulse-direct-spoof-stealth",
    }


def test_non_spoof_intent_buries_spoof_profiles():
    res = advise(PulseAdviseRequest(goal="mobile", cpu_cores=2, ram_mb=2048))
    spoof = next(p for p in res.profiles if p.profile_id == "pulse-direct-spoof-udp")
    assert spoof.score <= 12
    assert res.profiles[0].profile_id.startswith("pulse-reverse") or res.profiles[0].carrier != "spoof"


def test_reverse_profiles_untouched_for_mobile():
    res = advise(PulseAdviseRequest(goal="mobile", cpu_cores=1, ram_mb=1024))
    stealth = next(p for p in res.profiles if p.profile_id == "pulse-reverse-tcp-stealth")
    assert stealth.tunnel_mode == "reverse_stealth"
    assert stealth.carrier == "stealth"
    xdi = next(p for p in res.profiles if p.profile_id == "pulse-reverse-xdi")
    assert xdi.tunnel_mode == "reverse_xdi"
    assert xdi.carrier == "xdi"


def test_default_spoof_config_from_profiles():
    udp = default_spoof_config("pulse-direct-spoof-udp")
    assert udp is not None
    assert udp["profile"] == "udp"
    assert udp["stealth"] is False
    stealth = default_spoof_config("pulse-direct-spoof-stealth")
    assert stealth["stealth"] is True
    assert default_spoof_config("pulse-reverse-tcp-stealth") is None


def test_assert_spoof_rejects_reverse():
    with pytest.raises(ValueError, match="Direct L3 only"):
        assert_spoof_direct_only(tunnel_mode="reverse_stealth", carrier="spoof")
    assert_spoof_direct_only(tunnel_mode="direct_l3", carrier="spoof")
    assert_spoof_direct_only(tunnel_mode="reverse_stealth", carrier="stealth")


def test_render_spoof_autofills_peer_ip_on_iran():
    pulse = _spoof_pulse()
    iran = render_for_side("iran", pulse, "secret-token")
    abroad = render_for_side("abroad", pulse, "secret-token")
    assert 'carrier = "spoof"' in iran
    assert 'spoof_profile = "udp"' in iran
    assert 'spoof_peer_ip = "5.6.7.8"' in iran
    assert 'spoof_peer_ip = "1.2.3.4"' in abroad
    assert "spoof_src_ip" not in iran  # empty first-run
    assert "[server]" not in iran
    assert "[client]" not in abroad
    assert 'mode = "dial"' in iran
    assert 'mode = "listen"' in abroad


def test_render_spoof_stealth_bundle_and_src():
    pulse = _spoof_pulse(
        profile_id="pulse-direct-spoof-stealth",
        spoof_config={
            "profile": "udp",
            "stealth": True,
            "src_ip": "8.8.8.8",
            "src_pool": ["8.8.4.4"],
            "mtu": 1200,
            "sockbuf": 8388608,
            "icmp_reply": False,
        },
    )
    toml = render_for_side("iran", pulse, "tok")
    assert "spoof_padding = true" in toml
    assert "spoof_ttl_jitter = true" in toml
    assert "spoof_random_dscp = true" in toml
    assert "spoof_shuffle_port = true" in toml
    assert 'spoof_src_ip = "8.8.8.8"' in toml
    assert "spoof_mtu = 1200" in toml
    assert "spoof_sockbuf = 8388608" in toml


def test_render_refuses_reverse_plus_spoof():
    pulse = _spoof_pulse(tunnel_mode="reverse_tcp", carrier="spoof")
    with pytest.raises(ValueError, match="Direct L3 only"):
        render_for_side("iran", pulse, "tok")


def test_spoof_profile_meta():
    meta = profile_meta("pulse-direct-spoof-icmp")
    assert meta["carrier"] == "spoof"
    assert meta["tunnel_mode"] == "direct_l3"
    assert meta["spoof_profile"] == "icmp"
