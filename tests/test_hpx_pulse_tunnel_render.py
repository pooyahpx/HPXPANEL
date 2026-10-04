"""HPX Pulse tunnel TOML rendering — port forwards and multi-profile coverage."""

from types import SimpleNamespace

from app.services.hpx_pulse.tunnel_render import (
    MTU_HARD_MSS,
    MTU_SAFE_MSS,
    _normalize_reverse_ports,
    render_for_side,
    render_iran_server,
    resolve_mss,
)


def _pulse(**kwargs):
    defaults = {
        "tunnel_mode": "reverse_stealth",
        "carrier": "stealth",
        "preset": "balance",
        "profile_id": "pulse-reverse-tcp-stealth",
        "control_port": 47887,
        "iran_public_ip": "1.2.3.4",
        "abroad_public_ip": "5.6.7.8",
        "port_forwards": ["443"],
        "domain": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_normalize_reverse_ports_simple_and_mapped():
    assert _normalize_reverse_ports(["443"]) == ["443=127.0.0.1:443"]
    assert _normalize_reverse_ports(["443=8443"]) == ["443=127.0.0.1:8443"]
    assert _normalize_reverse_ports(["443=10.0.0.5:8443"]) == ["443=10.0.0.5:8443"]


def test_normalize_reverse_ports_multiple_do_not_collide():
    ports = _normalize_reverse_ports(["443", "2053", "8443=9443"])
    assert ports == [
        "443=127.0.0.1:443",
        "2053=127.0.0.1:2053",
        "8443=127.0.0.1:9443",
    ]


def test_render_iran_server_includes_all_forward_ports():
    toml = render_iran_server(
        control_port=2053,
        token="tok",
        transport="stealth",
        preset="balance",
        port_forwards=["443", "2053"],
    )
    assert 'bind_addr = "0.0.0.0:2053"' in toml
    assert '"443=127.0.0.1:443"' in toml
    assert '"2053=127.0.0.1:2053"' in toml
    assert "mss = 1280" in toml
    assert "accept_udp = true" in toml


def test_render_for_side_iran_and_abroad_share_token_but_not_ports_block_on_abroad():
    pulse = _pulse(port_forwards=["443", "2053"], control_port=47887)
    iran_toml = render_for_side("iran", pulse, "secret")
    abroad_toml = render_for_side("abroad", pulse, "secret")
    assert "ports = [" in iran_toml
    assert "443=127.0.0.1:443" in iran_toml
    assert "2053=127.0.0.1:2053" in iran_toml
    assert "ports" not in abroad_toml
    assert 'remote_addr = "1.2.3.4:47887"' in abroad_toml


def test_mtu_safe_profile_emits_mss_1200_both_sides():
    pulse = _pulse(profile_id="pulse-reverse-tcp-stealth-mtu")
    assert resolve_mss(pulse) == MTU_SAFE_MSS
    iran = render_for_side("iran", pulse, "tok")
    abroad = render_for_side("abroad", pulse, "tok")
    assert "mss = 1200" in iran
    assert "mss = 1200" in abroad
    assert 'preset = "balance"' in iran
    assert 'transport = "stealth"' in iran


def test_mtu_hard_profile_emits_mss_1100():
    pulse = _pulse(profile_id="pulse-reverse-tcp-stealth-mtu-hard")
    assert resolve_mss(pulse) == MTU_HARD_MSS
    assert "mss = 1100" in render_for_side("iran", pulse, "tok")
    assert "mss = 1100" in render_for_side("abroad", pulse, "tok")


def test_default_profile_keeps_mss_1280():
    pulse = _pulse(profile_id="pulse-reverse-tcp-stealth")
    assert "mss = 1280" in render_for_side("iran", pulse, "tok")
    assert "mss = 1280" in render_for_side("abroad", pulse, "tok")
