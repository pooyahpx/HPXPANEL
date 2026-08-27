"""Rule-based Pulse advisor — selects vetted HPX profiles, never invents ciphers."""

from app.models.hpx_pulse import (
    PulseAdviseRequest,
    PulseAdviseResponse,
    PulseProfileOption,
    PulseRealityFrontAdvice,
)

_PROFILES: dict[str, dict] = {
    "pulse-reverse-tcp-stealth": {
        "title": "Reverse TCP Stealth",
        "title_fa": "Reverse TCP Stealth",
        "tunnel_mode": "reverse_stealth",
        "carrier": "stealth",
        "preset": "balance",
        "base_score": 94,
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
        "preset": "balance",
        "base_score": 58,
    },
    "pulse-reverse-quic": {
        "title": "Reverse QUIC",
        "title_fa": "Reverse QUIC",
        "tunnel_mode": "reverse_quic",
        "carrier": "quic",
        "preset": "balance",
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
    "pulse-clean-udp": {
        "title": "Clean Direct (UDP)",
        "title_fa": "دایرکت UDP تمیز",
        "tunnel_mode": "direct_l3",
        "carrier": "udp",
        "preset": "balance",
        "base_score": 55,
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


def _score_reverse_base(req: PulseAdviseRequest, low_cpu: bool, score: int, reasons: list[str], reasons_fa: list[str]) -> int:
    reasons.append("HPX Reverse — Iran listens, abroad dials (port-forward topology)")
    reasons_fa.append("HPX Reverse — ایران گوش می‌دهد، خارج وصل می‌شود (port forward)")
    if req.goal in {"stealth", "balanced"}:
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

        if pid == "pulse-reverse-tcp-stealth":
            score = _score_reverse_base(req, low_cpu, score, reasons, reasons_fa)
            reasons.append("Noise-encrypted TCP — no TLS fingerprint, survives DPI")
            reasons_fa.append("TCP رمزنگاری‌شده — بدون fingerprint TLS، مناسب DPI")
            if req.goal in {"stealth", "balanced"}:
                score += 10
            if low_cpu:
                score += 6
                reasons.append("Light on single-core — best default for port forwards")
                reasons_fa.append("سبک روی تک‌هسته — بهترین پیش‌فرض برای port forward")
            if req.goal == "speed":
                score -= 5

        elif pid == "pulse-reverse-tcp":
            score = _score_reverse_base(req, low_cpu, score, reasons, reasons_fa)
            reasons.append("Plain reverse TCP — lowest CPU on port-forward setups")
            reasons_fa.append("Reverse TCP ساده — کمترین CPU برای port forward")
            if req.goal == "speed":
                score += 8
            if req.goal == "stealth":
                score -= 15
                opt_warnings.append("Plain TCP is easier to fingerprint than Stealth")

        elif pid == "pulse-reverse-tcp-mux":
            score = _score_reverse_base(req, low_cpu, score, reasons, reasons_fa)
            reasons.append("Multiplexed TCP — many short connections on one tunnel")
            reasons_fa.append("TCP Mux — اتصالات کوتاه زیاد روی یک تونل")
            if req.goal == "speed":
                score += 5

        elif pid in {"pulse-reverse-wss", "pulse-reverse-wss-mux"}:
            score = _score_reverse_base(req, low_cpu, score, reasons, reasons_fa)
            reasons.append("Looks like ordinary HTTPS — CDN-friendly")
            reasons_fa.append("شبیه HTTPS عادی — مناسب CDN")
            if req.goal == "stealth":
                score += 12
            if not domain:
                score -= 20
                opt_warnings.append("Set domain on Iran for Let's Encrypt certificate")

        elif pid == "pulse-reverse-ws":
            score = _score_reverse_base(req, low_cpu, score, reasons, reasons_fa)
            reasons.append("HTTP WebSocket carrier — when only HTTP gets through")
            reasons_fa.append("حامل WebSocket — وقتی فقط HTTP رد می‌شود")

        elif pid == "pulse-reverse-kcp":
            score = _score_reverse_base(req, low_cpu, score, reasons, reasons_fa)
            if loss >= 8 or req.udp_reachable is True:
                score += 15 if loss >= 8 else 5
                reasons.append("High packet loss: KCP+FEC repairs without waiting RTT")
                reasons_fa.append("لاس بالا: KCP+FEC بدون انتظار RTT تعمیر می‌کند")
            else:
                score -= 10
            if low_cpu:
                opt_warnings.append("KCP+FEC uses more CPU and bandwidth than Stealth")

        elif pid == "pulse-reverse-udp":
            score = _score_reverse_base(req, low_cpu, score, reasons, reasons_fa)
            if req.udp_reachable is False:
                score -= 35
                opt_warnings.append("UDP path reported blocked — not recommended")
            if req.goal == "speed":
                score += 8

        elif pid == "pulse-reverse-quic":
            score = _score_reverse_base(req, low_cpu, score, reasons, reasons_fa)
            reasons.append("Encrypted UDP with self-tuning congestion control")
            reasons_fa.append("UDP رمزنگاری‌شده با کنترل ازدحام خودکار")

        elif pid == "pulse-reverse-xdi":
            score = _score_reverse_base(req, low_cpu, score, reasons, reasons_fa)
            reasons.append("ICMP echo carrier — when TCP/UDP are filtered but ping works")
            reasons_fa.append("حامل ICMP — وقتی TCP/UDP فیلترند ولی ping کار می‌کند")
            opt_warnings.append("Linux only — needs raw socket privileges")

        elif pid == "pulse-tcp-stealth":
            reasons.append("Direct L3 PCK — full L3 tunnel with TCP-shaped carrier")
            reasons_fa.append("Direct L3 با PCK — تونل لایه۳ با حامل شبیه TCP")
            if req.goal in {"stealth", "balanced"}:
                score += 8
            if low_cpu:
                score -= 20
                opt_warnings.append("1 CPU core: prefer Reverse TCP Stealth for port forwards")
                reasons.append("Heavy on 1 core — use Reverse Stealth unless you need L3")
                reasons_fa.append("روی ۱ هسته سنگین است — برای port forward از Reverse Stealth استفاده کن")

        elif pid == "pulse-stealth-balance":
            if low_cpu:
                score -= 12
                opt_warnings.append("1 CPU core: prefer pulse-reverse-tcp-stealth")
            else:
                reasons.append("Filtered path: PCK carrier hides socket fingerprint")
                reasons_fa.append("مسیر فیلترشده: PCK اثر TCP بدون سوکت واقعی")
            if req.goal == "stealth":
                score += 5
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
        warnings.append("1 CPU core — Reverse TCP Stealth is the recommended default for port forwards")
    if loss > 15:
        warnings.append("High packet loss — consider pulse-reverse-kcp")

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
