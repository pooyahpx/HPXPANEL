"""P4 Pulse advisor intents and engine presets."""

from app.models.hpx_pulse import PulseAdviseRequest
from app.services.hpx_pulse.advisor import advise, profile_meta


def test_mobile_intent_prefers_balance_stealth():
    res = advise(PulseAdviseRequest(goal="mobile", cpu_cores=1, ram_mb=1024))
    top = res.profiles[0]
    assert top.profile_id in {
        "pulse-reverse-tcp-stealth",
        "pulse-reverse-tcp-stealth-mtu",
        "pulse-reverse-tcp-stealth-mtu-hard",
        "pulse-reverse-wss",
        "pulse-reverse-wss-mux",
        "pulse-reverse-kcp",
        "pulse-reverse-quic",
    }
    assert top.preset in {"balance", "turbo"}


def test_tcp_extreme_profile_mss_1000():
    from app.services.hpx_pulse.tunnel_render import render_for_side
    from types import SimpleNamespace

    pulse = SimpleNamespace(
        profile_id="pulse-reverse-tcp-stealth-mtu-extreme",
        tunnel_mode="reverse_stealth",
        carrier="stealth",
        preset="balance",
        control_port=9000,
        iran_public_ip="1.1.1.1",
        abroad_public_ip="2.2.2.2",
        port_forwards=["443=127.0.0.1:443"],
        domain=None,
        mss=None,
    )
    iran = render_for_side("iran", pulse, "tok")
    abroad = render_for_side("abroad", pulse, "tok")
    assert "mss = 1000" in iran
    assert "mss = 1000" in abroad
    assert 'transport = "stealth"' in iran


def test_hard_intent_surfaces_udp_escape():
    res = advise(PulseAdviseRequest(goal="hard", cpu_cores=4, ram_mb=2048))
    top_ids = {p.profile_id for p in res.profiles[:5]}
    # TCP Extreme should surface for hard; UDP escape may also appear further down.
    assert "pulse-reverse-tcp-stealth-mtu-extreme" in top_ids or top_ids & {
        "pulse-tcp-pass-kcp",
        "pulse-reverse-kcp",
    }


def test_tcp_pass_profiles_exist():
    res = advise(PulseAdviseRequest(goal="hard", cpu_cores=2, ram_mb=2048))
    kcp = next(p for p in res.profiles if p.profile_id == "pulse-tcp-pass-kcp")
    quic = next(p for p in res.profiles if p.profile_id == "pulse-tcp-pass-quic")
    assert kcp.tunnel_mode == "reverse_kcp"
    assert kcp.carrier == "kcp"
    assert quic.tunnel_mode == "reverse_quic"
    assert "TCP" in kcp.title or "KCP" in kcp.title
    # Hard intent ranks TCP Extreme/Safe first; Escape/KCP still listed below.
    assert res.profiles[0].profile_id in {
        "pulse-reverse-tcp-stealth-mtu-extreme",
        "pulse-reverse-tcp-stealth-mtu-hard",
        "pulse-reverse-tcp-stealth-mtu",
        "pulse-reverse-tcp-stealth",
        "pulse-tcp-pass-kcp",
        "pulse-tcp-pass-quic",
        "pulse-reverse-kcp",
    }
    assert any(p.profile_id == "pulse-tcp-pass-kcp" for p in res.profiles[:12])


def test_hard_intent_surfaces_aggressive_when_cpu_allows():
    res = advise(PulseAdviseRequest(goal="hard", cpu_cores=4, ram_mb=2048))
    aggressive = [p for p in res.profiles if p.preset == "aggressive"]
    assert aggressive
    assert any(p.profile_id.endswith("hard") or "aggressive" in p.profile_id for p in res.profiles[:8])


def test_fast_intent_boosts_turbo_carriers():
    res = advise(PulseAdviseRequest(goal="fast", cpu_cores=2, ram_mb=2048, udp_reachable=True))
    top_ids = {p.profile_id for p in res.profiles[:4]}
    assert top_ids & {"pulse-reverse-kcp", "pulse-reverse-quic", "pulse-reverse-udp", "pulse-clean-udp"}


def test_low_cpu_forces_aggressive_to_balance():
    meta = profile_meta("pulse-reverse-tcp-stealth-hard")
    assert meta["preset"] == "aggressive"
    res = advise(PulseAdviseRequest(goal="hard", cpu_cores=1, ram_mb=512), profile_override="pulse-reverse-tcp-stealth-hard")
    chosen = next(p for p in res.profiles if p.profile_id == "pulse-reverse-tcp-stealth-hard")
    assert chosen.preset == "balance"


def test_profile_meta_fallback():
    meta = profile_meta("does-not-exist")
    assert meta["profile_id"] == "pulse-reverse-tcp-stealth"


def test_mtu_safe_profiles_exposed_with_mss():
    res = advise(PulseAdviseRequest(goal="mobile", cpu_cores=1, ram_mb=1024))
    mtu = next(p for p in res.profiles if p.profile_id == "pulse-reverse-tcp-stealth-mtu")
    hard = next(p for p in res.profiles if p.profile_id == "pulse-reverse-tcp-stealth-mtu-hard")
    assert mtu.mss == 1200
    assert hard.mss == 1100
    assert mtu.preset == "balance"
    assert mtu.tunnel_mode == "reverse_stealth"
    ids = {p.profile_id for p in res.profiles}
    assert "pulse-reverse-tcp-stealth-mtu" in ids
    assert "pulse-tcp-pass-kcp" in ids


def test_mtu_profile_meta():
    meta = profile_meta("pulse-reverse-tcp-stealth-mtu")
    assert meta["mss"] == 1200
    assert meta["preset"] == "balance"

