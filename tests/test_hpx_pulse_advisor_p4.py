"""P4 Pulse advisor intents and engine presets."""

from app.models.hpx_pulse import PulseAdviseRequest
from app.services.hpx_pulse.advisor import advise, profile_meta


def test_mobile_intent_prefers_balance_stealth():
    res = advise(PulseAdviseRequest(goal="mobile", cpu_cores=1, ram_mb=1024))
    top = res.profiles[0]
    assert top.profile_id in {
        "pulse-reverse-tcp-stealth",
        "pulse-reverse-wss",
        "pulse-reverse-wss-mux",
    }
    assert top.preset == "balance"


def test_hard_intent_surfaces_aggressive_when_cpu_allows():
    res = advise(PulseAdviseRequest(goal="hard", cpu_cores=4, ram_mb=2048))
    aggressive = [p for p in res.profiles if p.preset == "aggressive"]
    assert aggressive
    assert any(p.profile_id.endswith("hard") or "aggressive" in p.profile_id for p in res.profiles[:5])


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
