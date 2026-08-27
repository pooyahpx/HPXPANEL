"""Rule-based Pulse advisor — selects vetted profiles, never invents ciphers."""

from app.models.hpx_pulse import (
    PulseAdviseRequest,
    PulseAdviseResponse,
    PulseProfileOption,
    PulseRealityFrontAdvice,
)

_PROFILES: dict[str, dict] = {
    "pulse-tcp-stealth": {
        "title": "Direct TCP Stealth (PCK)",
        "title_fa": "دایرکت TCP Stealth (PCK)",
        "tunnel_mode": "direct_l3",
        "carrier": "pck",
        "preset": "balance",
        "base_score": 88,
    },
    "pulse-stealth-balance": {
        "title": "Stealth Direct (Balance)",
        "title_fa": "دایرکت Stealth (Balance)",
        "tunnel_mode": "direct_l3",
        "carrier": "pck",
        "preset": "balance",
        "base_score": 85,
    },
    "pulse-clean-udp": {
        "title": "Clean Direct (UDP)",
        "title_fa": "دایرکت UDP تمیز",
        "tunnel_mode": "direct_l3",
        "carrier": "udp",
        "preset": "balance",
        "base_score": 55,
    },
    "pulse-lossy-kcp": {
        "title": "Lossy path (Reverse KCP+FEC)",
        "title_fa": "مسیر پرلاس (Reverse KCP+FEC)",
        "tunnel_mode": "reverse_kcp",
        "carrier": None,
        "preset": "turbo",
        "base_score": 75,
    },
}


def _reality_front(domain: str | None, sni_hint: str | None) -> PulseRealityFrontAdvice:
    sni = sni_hint or "play.google.com"
    dest = f"{sni}:443"
    checklist = [
        f"Point domain A record to Iran public IP{f' ({domain})' if domain else ''}",
        f"Run on Iran: curl -I --max-time 5 https://{sni}",
        f"Reality dest={dest}, serverNames={sni}",
        "Do not expose abroad IP to users — only Iran domain/inbound",
    ]
    checklist_fa = [
        f"دامنه را A record به IP ایران بده{f' ({domain})' if domain else ''}",
        f"روی ایران: curl -I --max-time 5 https://{sni}",
        f"Reality: dest={dest}, serverNames={sni}",
        "IP خارج را به کاربر نده — فقط دامنه/اینباند ایران",
    ]
    return PulseRealityFrontAdvice(
        domain_on_iran=True,
        sni=sni,
        dest=dest,
        checklist=checklist,
        checklist_fa=checklist_fa,
    )


def advise(
    req: PulseAdviseRequest,
    *,
    domain: str | None = None,
    sni_hint: str | None = None,
    profile_override: str | None = None,
) -> PulseAdviseResponse:
    warnings: list[str] = []
    options: list[PulseProfileOption] = []

    loss = req.packet_loss_pct if req.packet_loss_pct is not None else 0.0
    low_cpu = req.cpu_cores < 2

    for pid, meta in _PROFILES.items():
        score = meta["base_score"]
        reasons: list[str] = []
        reasons_fa: list[str] = []
        opt_warnings: list[str] = []
        carrier = meta["carrier"]
        preset = meta["preset"]
        tunnel_mode = meta["tunnel_mode"]

        if pid == "pulse-tcp-stealth":
            reasons.append("TCP-shaped stealth carrier (PCK) — best default for filtered paths")
            reasons_fa.append("حامل TCP Stealth (PCK) — پیش‌فرض مناسب برای مسیر فیلترشده")
            if req.goal in {"stealth", "balanced"}:
                score += 12
            if low_cpu:
                score -= 15
                opt_warnings.append("1 CPU core: PCK is CPU-heavy — consider 2+ cores or UDP profile")
                reasons.append("Single-core: PCK works but CPU will spike under load")
                reasons_fa.append("تک‌هسته: PCK کار می‌کند ولی CPU زیر بار بالا می‌رود")
            reasons.append("Direct L3 + Noise/GRE — HPX Direct tunnel")
            reasons_fa.append("Direct L3 + Noise/GRE — تونل HPX Direct")

        elif pid == "pulse-stealth-balance":
            if low_cpu:
                score -= 10
                opt_warnings.append("1 CPU core: prefer pulse-tcp-stealth with Balance preset")
            else:
                reasons.append("Filtered path: PCK carrier hides socket fingerprint")
                reasons_fa.append("مسیر فیلترشده: PCK اثر TCP بدون سوکت واقعی")
            if req.goal == "stealth":
                score += 8
            reasons.append("Direct L3 + Noise/GRE inside HPX engine")
            reasons_fa.append("Direct L3 با GRE+Noise")

        elif pid == "pulse-clean-udp":
            if req.goal in {"stealth", "balanced"}:
                score -= 10
            if req.goal == "speed":
                score += 10
            if req.udp_reachable is False:
                score -= 40
                opt_warnings.append("UDP path reported blocked — not recommended")
            elif req.udp_reachable is True and loss < 5:
                score += 15
                reasons.append("Clean UDP path with low loss")
                reasons_fa.append("مسیر UDP تمیز با لاس کم")
            reasons.append("Lowest CPU overhead on clean routes")
            reasons_fa.append("کمترین مصرف CPU روی مسیر تمیز")

        elif pid == "pulse-lossy-kcp":
            if loss >= 8 or req.udp_reachable is True:
                score += 15 if loss >= 8 else 5
                reasons.append("High packet loss: KCP+FEC repairs without waiting RTT")
                reasons_fa.append("لاس بالا: KCP+FEC بدون انتظار RTT تعمیر می‌کند")
            else:
                score -= 10
            reasons.append("Uses reverse/port KCP — not Direct L3 (BackPack limitation)")
            reasons_fa.append("Reverse/port KCP — نه Direct L3 (محدودیت BackPack)")
            if tunnel_mode == "reverse_kcp":
                opt_warnings.append("Configure reverse KCP tunnel separately on both hosts")

        if req.ram_mb < 768:
            score -= 10
            opt_warnings.append("Low RAM — use Balance preset only")

        options.append(
            PulseProfileOption(
                profile_id=pid,
                title=meta["title"],
                title_fa=meta["title_fa"],
                tunnel_mode=tunnel_mode,
                carrier=carrier,
                preset=preset if not (low_cpu and preset == "aggressive") else "balance",
                score=max(0, min(100, score)),
                reasons=reasons,
                reasons_fa=reasons_fa,
                warnings=opt_warnings,
            )
        )

    options.sort(key=lambda o: o.score, reverse=True)
    recommended = profile_override if profile_override in _PROFILES else options[0].profile_id

    if low_cpu:
        warnings.append("1 CPU core detected — avoid PCK Aggressive and heavy presets")
    if loss > 15:
        warnings.append("High packet loss — consider pulse-lossy-kcp reverse path")

    return PulseAdviseResponse(
        recommended_profile_id=recommended,
        profiles=options,
        reality_front=_reality_front(domain, sni_hint),
        warnings=warnings,
    )


def profile_meta(profile_id: str) -> dict:
    if profile_id not in _PROFILES:
        profile_id = "pulse-tcp-stealth"
    return {"profile_id": profile_id, **_PROFILES[profile_id]}
