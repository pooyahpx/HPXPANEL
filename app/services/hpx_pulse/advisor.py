"""Rule-based Pulse advisor — selects vetted HPX profiles, never invents ciphers."""

from app.models.hpx_pulse import (
    PulseAdviseRequest,
    PulseAdviseResponse,
    PulseProfileOption,
    PulseRealityFrontAdvice,
)

# Operator intents map onto classic goals for scoring.
_GOAL_ALIAS = {
    "mobile": "stealth",
    "hard": "stealth",
    "fast": "speed",
    "stealth": "stealth",
    "balanced": "balanced",
    "speed": "speed",
}

_PROFILES: dict[str, dict] = {
    "pulse-reverse-tcp-stealth": {
        "title": "Reverse TCP Stealth",
        "title_fa": "Reverse TCP Stealth",
        "tunnel_mode": "reverse_stealth",
        "carrier": "stealth",
        "preset": "balance",
        "base_score": 94,
    },
    "pulse-reverse-tcp-stealth-hard": {
        "title": "Reverse TCP Stealth (Hard)",
        "title_fa": "Reverse TCP Stealth (سخت)",
        "tunnel_mode": "reverse_stealth",
        "carrier": "stealth",
        "preset": "aggressive",
        "base_score": 92,
    },
    "pulse-reverse-tcp": {
        "title": "Reverse TCP",
        "title_fa": "Reverse TCP",
        "tunnel_mode": "reverse_tcp",
        "carrier": "tcp",
        "preset": "balance",
        "base_score": 72,
    },
    "pulse-reverse-tcp-mux": {
        "title": "Reverse TCP Mux",
        "title_fa": "Reverse TCP Mux",
        "tunnel_mode": "reverse_tcpmux",
        "carrier": "tcpmux",
        "preset": "balance",
        "base_score": 68,
    },
    "pulse-reverse-wss": {
        "title": "Reverse WSS (HTTPS look)",
        "title_fa": "Reverse WSS (شبیه HTTPS)",
        "tunnel_mode": "reverse_wss",
        "carrier": "wss",
        "preset": "balance",
        "base_score": 86,
    },
    "pulse-reverse-wss-mux": {
        "title": "Reverse WSS Mux",
        "title_fa": "Reverse WSS Mux",
        "tunnel_mode": "reverse_wssmux",
        "carrier": "wssmux",
        "preset": "balance",
        "base_score": 82,
    },
    "pulse-reverse-ws": {
        "title": "Reverse WebSocket",
        "title_fa": "Reverse WebSocket",
        "tunnel_mode": "reverse_ws",
        "carrier": "ws",
        "preset": "balance",
        "base_score": 70,
    },
    "pulse-reverse-kcp": {
        "title": "Reverse KCP + FEC",
        "title_fa": "Reverse KCP + FEC",
        "tunnel_mode": "reverse_kcp",
        "carrier": "kcp",
        "preset": "turbo",
        "base_score": 75,
    },
    "pulse-reverse-udp": {
        "title": "Reverse UDP",
        "title_fa": "Reverse UDP",
        "tunnel_mode": "reverse_udp",
        "carrier": "udp",
        "preset": "turbo",
        "base_score": 58,
    },
    "pulse-reverse-quic": {
        "title": "Reverse QUIC",
        "title_fa": "Reverse QUIC",
        "tunnel_mode": "reverse_quic",
        "carrier": "quic",
        "preset": "turbo",
        "base_score": 64,
    },
    "pulse-reverse-xdi": {
        "title": "Reverse ICMP (xDi)",
        "title_fa": "Reverse ICMP (xDi)",
        "tunnel_mode": "reverse_xdi",
        "carrier": "xdi",
        "preset": "balance",
        "base_score": 62,
    },
    "pulse-tcp-stealth": {
        "title": "Direct TCP Stealth (PCK)",
        "title_fa": "دایرکت TCP Stealth (PCK)",
        "tunnel_mode": "direct_l3",
        "carrier": "pck",
        "preset": "balance",
        "base_score": 78,
    },
    "pulse-stealth-balance": {
        "title": "Stealth Direct (Balance)",
        "title_fa": "دایرکت Stealth (Balance)",
        "tunnel_mode": "direct_l3",
        "carrier": "pck",
        "preset": "balance",
        "base_score": 75,
    },
    "pulse-stealth-aggressive": {
        "title": "Stealth Direct (Aggressive)",
        "title_fa": "دایرکت Stealth (Aggressive)",
        "tunnel_mode": "direct_l3",
        "carrier": "pck",
        "preset": "aggressive",
        "base_score": 76,
    },
    "pulse-clean-udp": {
        "title": "Clean Direct (UDP)",
        "title_fa": "دایرکت UDP تمیز",
        "tunnel_mode": "direct_l3",
        "carrier": "udp",
        "preset": "turbo",
        "base_score": 55,
    },
}


def _normalize_goal(goal: str) -> str:
    return _GOAL_ALIAS.get(goal, "balanced")


def _intent_preset_boost(intent: str, preset: str) -> int:
    if intent == "mobile" and preset == "balance":
        return 8
    if intent == "hard" and preset == "aggressive":
        return 12
    if intent == "fast" and preset in {"turbo", "aggressive"}:
        return 10
    if intent == "hard" and preset == "balance":
        return 2
    return 0


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


def _score_reverse_base(goal: str, low_cpu: bool, score: int, reasons: list[str], reasons_fa: list[str]) -> int:
    reasons.append("HPX Reverse — Iran listens, abroad dials (port-forward topology)")
    reasons_fa.append("HPX Reverse — ایران گوش می‌دهد، خارج وصل می‌شود (port forward)")
    if goal in {"stealth", "balanced"}:
        score += 6
    if low_cpu:
        score += 4
    return score


def advise(
    req: PulseAdviseRequest,
    *,
    domain: str | None = None,
    sni_hint: str | None = None,
    profile_override: str | None = None,
) -> PulseAdviseResponse:
    warnings: list[str] = []
    options: list[PulseProfileOption] = []

    intent = req.goal
    goal = _normalize_goal(intent)
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

        score += _intent_preset_boost(intent, preset)

        if pid in {"pulse-reverse-tcp-stealth", "pulse-reverse-tcp-stealth-hard"}:
            score = _score_reverse_base(goal, low_cpu, score, reasons, reasons_fa)
            reasons.append("Noise-encrypted TCP — no TLS fingerprint, survives DPI")
            reasons_fa.append("TCP رمزنگاری‌شده — بدون fingerprint TLS، مناسب DPI")
            if goal in {"stealth", "balanced"}:
                score += 10
            if intent == "mobile" and preset == "balance":
                score += 8
                reasons.append("Balance preset — best for phones and single-core VPS")
                reasons_fa.append("Preset Balance — مناسب موبایل و VPS تک‌هسته")
            if intent == "hard" and preset == "aggressive":
                score += 10
                reasons.append("Aggressive stealth shaping for harsh DPI")
                reasons_fa.append("شکل‌دهی Stealth تهاجمی برای DPI سخت")
            if low_cpu and preset == "aggressive":
                score -= 25
                opt_warnings.append("Aggressive preset needs ≥2 CPU cores")
            if low_cpu and preset == "balance":
                score += 6
                reasons.append("Light on single-core — best default for port forwards")
                reasons_fa.append("سبک روی تک‌هسته — بهترین پیش‌فرض برای port forward")
            if goal == "speed":
                score -= 5

        elif pid == "pulse-reverse-tcp":
            score = _score_reverse_base(goal, low_cpu, score, reasons, reasons_fa)
            reasons.append("Plain reverse TCP — lowest CPU on port-forward setups")
            reasons_fa.append("Reverse TCP ساده — کمترین CPU برای port forward")
            if goal == "speed":
                score += 8
            if goal == "stealth":
                score -= 15
                opt_warnings.append("Plain TCP is easier to fingerprint than Stealth")

        elif pid == "pulse-reverse-tcp-mux":
            score = _score_reverse_base(goal, low_cpu, score, reasons, reasons_fa)
            reasons.append("Multiplexed TCP — many short connections on one tunnel")
            reasons_fa.append("TCP Mux — اتصالات کوتاه زیاد روی یک تونل")
            if goal == "speed":
                score += 5

        elif pid in {"pulse-reverse-wss", "pulse-reverse-wss-mux"}:
            score = _score_reverse_base(goal, low_cpu, score, reasons, reasons_fa)
            reasons.append("Looks like ordinary HTTPS — CDN-friendly")
            reasons_fa.append("شبیه HTTPS عادی — مناسب CDN")
            if goal == "stealth" or intent == "mobile":
                score += 12
            if not domain:
                score -= 20
                opt_warnings.append("Set domain on Iran for Let's Encrypt certificate")

        elif pid == "pulse-reverse-ws":
            score = _score_reverse_base(goal, low_cpu, score, reasons, reasons_fa)
            reasons.append("HTTP WebSocket carrier — when only HTTP gets through")
            reasons_fa.append("حامل WebSocket — وقتی فقط HTTP رد می‌شود")

        elif pid == "pulse-reverse-kcp":
            score = _score_reverse_base(goal, low_cpu, score, reasons, reasons_fa)
            if loss >= 8 or req.udp_reachable is True or intent == "fast":
                score += 15 if loss >= 8 or intent == "fast" else 5
                reasons.append("High loss / speed intent: KCP+FEC turbo preset")
                reasons_fa.append("لاس بالا / قصد سرعت: KCP+FEC با preset turbo")
            else:
                score -= 10
            if low_cpu:
                opt_warnings.append("KCP+FEC uses more CPU and bandwidth than Stealth")

        elif pid == "pulse-reverse-udp":
            score = _score_reverse_base(goal, low_cpu, score, reasons, reasons_fa)
            if req.udp_reachable is False:
                score -= 35
                opt_warnings.append("UDP path reported blocked — not recommended")
            if goal == "speed" or intent == "fast":
                score += 8

        elif pid == "pulse-reverse-quic":
            score = _score_reverse_base(goal, low_cpu, score, reasons, reasons_fa)
            reasons.append("Encrypted UDP with self-tuning congestion control")
            reasons_fa.append("UDP رمزنگاری‌شده با کنترل ازدحام خودکار")
            if intent == "fast":
                score += 10

        elif pid == "pulse-reverse-xdi":
            score = _score_reverse_base(goal, low_cpu, score, reasons, reasons_fa)
            reasons.append("ICMP echo carrier — when TCP/UDP are filtered but ping works")
            reasons_fa.append("حامل ICMP — وقتی TCP/UDP فیلترند ولی ping کار می‌کند")
            opt_warnings.append("Linux only — needs raw socket privileges")
            if intent == "hard":
                score += 8

        elif pid == "pulse-tcp-stealth":
            reasons.append("Direct L3 PCK — full L3 tunnel with TCP-shaped carrier")
            reasons_fa.append("Direct L3 با PCK — تونل لایه۳ با حامل شبیه TCP")
            if goal in {"stealth", "balanced"}:
                score += 8
            if low_cpu:
                score -= 20
                opt_warnings.append("1 CPU core: prefer Reverse TCP Stealth for port forwards")

        elif pid == "pulse-stealth-balance":
            if low_cpu:
                score -= 12
                opt_warnings.append("1 CPU core: prefer pulse-reverse-tcp-stealth")
            else:
                reasons.append("Filtered path: PCK carrier hides socket fingerprint")
                reasons_fa.append("مسیر فیلترشده: PCK اثر TCP بدون سوکت واقعی")
            if goal == "stealth":
                score += 5

        elif pid == "pulse-stealth-aggressive":
            if low_cpu:
                score -= 30
                opt_warnings.append("Aggressive direct stealth needs ≥2 CPU cores")
            if intent == "hard":
                score += 12
                reasons.append("Maximum stealth shaping on Direct L3")
                reasons_fa.append("حداکثر شکل‌دهی stealth روی Direct L3")
            else:
                score -= 5

        elif pid == "pulse-clean-udp":
            if goal in {"stealth", "balanced"}:
                score -= 10
            if goal == "speed" or intent == "fast":
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

        if req.ram_mb < 768:
            score -= 10
            opt_warnings.append("Low RAM — use Balance preset only")
            if preset == "aggressive":
                score -= 15

        effective_preset = preset
        if low_cpu and preset == "aggressive":
            effective_preset = "balance"

        options.append(
            PulseProfileOption(
                profile_id=pid,
                title=meta["title"],
                title_fa=meta["title_fa"],
                tunnel_mode=tunnel_mode,
                carrier=carrier,
                preset=effective_preset,
                score=max(0, min(100, score)),
                reasons=reasons,
                reasons_fa=reasons_fa,
                warnings=opt_warnings,
            )
        )

    options.sort(key=lambda o: o.score, reverse=True)
    recommended = profile_override if profile_override in _PROFILES else options[0].profile_id

    if low_cpu:
        warnings.append("1 CPU core — Reverse TCP Stealth (Balance) is the recommended default")
    if loss > 15:
        warnings.append("High packet loss — consider pulse-reverse-kcp")
    if intent == "hard":
        warnings.append("Hard intent prefers Aggressive stealth presets when CPU allows")
    if intent == "mobile":
        warnings.append("Mobile intent prefers Balance + Reverse Stealth / WSS")

    return PulseAdviseResponse(
        recommended_profile_id=recommended,
        profiles=options,
        reality_front=_reality_front(domain, sni_hint),
        warnings=warnings,
    )


def profile_meta(profile_id: str) -> dict:
    if profile_id not in _PROFILES:
        profile_id = "pulse-reverse-tcp-stealth"
    return {"profile_id": profile_id, **_PROFILES[profile_id]}
