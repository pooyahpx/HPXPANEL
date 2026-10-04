"""Panel-side Pulse path diagnostics (inspired by BackPack Health Check)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime as dt
from typing import Any, Literal

from app.db.models import HpxPulse, HpxPulseStatus
from app.services.hpx_pulse.healer import AGENT_STALE_SECONDS, _agent_stale, _aware

DiagLevel = Literal["ok", "warn", "fail", "info"]


@dataclass
class PulseDiagCheck:
    group: str
    name: str
    level: DiagLevel
    detail: str
    fix: str = ""


def _seconds_ago(value: dt | None) -> int | None:
    seen = _aware(value)
    if seen is None:
        return None
    return max(0, int((dt.now(UTC) - seen).total_seconds()))


def diagnose_pulse_record(pulse: HpxPulse) -> list[PulseDiagCheck]:
    """Explain why a Pulse may show disconnected / no ping — without SSH."""
    checks: list[PulseDiagCheck] = []
    g = f"Pulse: {pulse.name}"
    mode = pulse.tunnel_mode or "direct_l3"
    is_reverse = mode.startswith("reverse_")

    checks.append(
        PulseDiagCheck(
            g,
            "Status",
            "info" if pulse.status == HpxPulseStatus.running else "warn",
            f"{pulse.status}" + (f" — {pulse.message}" if pulse.message else ""),
            "" if pulse.status == HpxPulseStatus.running else "Open Diagnose on agents or Sync, then check Iran firewall + abroad backend",
        )
    )
    checks.append(
        PulseDiagCheck(
            g,
            "Mode",
            "info",
            f"{mode} / preset={pulse.preset or 'balance'} / carrier={pulse.carrier or '—'}",
        )
    )
    checks.append(
        PulseDiagCheck(
            g,
            "Endpoints",
            "ok" if pulse.iran_public_ip and pulse.abroad_public_ip else "fail",
            f"Iran {pulse.iran_public_ip or 'MISSING'} ⇄ Abroad {pulse.abroad_public_ip or 'MISSING'} · control {pulse.control_port}",
            "Set both public IPs and a free control port" if not (pulse.iran_public_ip and pulse.abroad_public_ip) else "",
        )
    )

    forwards = pulse.port_forwards or []
    if not forwards and is_reverse:
        checks.append(
            PulseDiagCheck(
                g,
                "Port forwards",
                "fail",
                "none — reverse tunnels need at least one forward (e.g. 443=127.0.0.1:443)",
                "Edit pulse → add port forwards matching Xray listen on abroad",
            )
        )
    else:
        checks.append(
            PulseDiagCheck(
                g,
                "Port forwards",
                "ok" if forwards else "info",
                ", ".join(forwards) if forwards else "none (L3 may not need them)",
            )
        )

    # Agents
    for side, claimed, host, seen in (
        ("Iran", bool(pulse.iran_agent_key_hash), pulse.iran_agent_host, pulse.iran_agent_last_seen),
        ("Abroad", bool(pulse.abroad_agent_key_hash), pulse.abroad_agent_host, pulse.abroad_agent_last_seen),
    ):
        if not claimed:
            checks.append(
                PulseDiagCheck(
                    g,
                    f"{side} agent",
                    "fail",
                    "not joined",
                    f"Tokens → run {side} join command on that VPS",
                )
            )
            continue
        age = _seconds_ago(seen)
        if age is None or _agent_stale(seen):
            checks.append(
                PulseDiagCheck(
                    g,
                    f"{side} agent",
                    "fail",
                    f"silent ({age if age is not None else 'never'}s ago, host={host or '—'})",
                    f"On {side} VPS: sudo hpx-pulse-agent sync && sudo hpx-pulse-agent ping — check PANEL_URL / firewall",
                )
            )
        else:
            checks.append(
                PulseDiagCheck(
                    g,
                    f"{side} agent",
                    "ok",
                    f"heartbeat {age}s ago · host={host or '—'}",
                )
            )

    # Ping / path
    if pulse.latency_ms is None:
        if is_reverse:
            checks.append(
                PulseDiagCheck(
                    g,
                    "Live ping",
                    "fail",
                    "no RTT — abroad cannot TCP-reach Iran control or forward port",
                    "1) Iran firewall: control + forward TCP ports  2) Abroad Xray on 127.0.0.1:<forward>  3) If UDP apps work but TCP stalls → Sync (mss=1360) or lower mss to 1280",
                )
            )
        else:
            checks.append(
                PulseDiagCheck(
                    g,
                    "Live ping",
                    "warn",
                    "no ICMP RTT on L3 peer (ICMP often blocked) — not the same as tunnel health",
                    "Check bp0 + tunnel service. If ICMP ping works but TCP pages stall → mss_clamp / Sync",
                )
            )
    else:
        level: DiagLevel = "ok"
        fix = ""
        msg_l = (pulse.message or "").lower()
        if pulse.latency_ms > 300:
            level = "warn"
            fix = "High RTT — try preset speed or a closer abroad VPS"
        if "control ok" in msg_l and ("closed" in msg_l or "forward" in msg_l):
            level = "fail"
            fix = "Tunnel control is up but user TCP port is dead — open Iran forward ports; ensure abroad backend listens"
        detail = f"{pulse.latency_ms:.1f} ms (TCP path RTT — not ICMP)"
        if pulse.message:
            detail += f" — {pulse.message}"
        checks.append(PulseDiagCheck(g, "Live ping", level, detail, fix))

    # Classic: UDP works, TCP stalls after connect → MSS/MTU.
    if is_reverse and pulse.status in {HpxPulseStatus.running, HpxPulseStatus.unhealthy, HpxPulseStatus.partial}:
        checks.append(
            PulseDiagCheck(
                g,
                "TCP vs UDP",
                "info",
                "If UDP (e.g. QUIC/WireGuard apps) works but TCP sites stall: path MTU — Pulse now sets mss=1360; Sync both agents",
                "Still broken? Edit TOML mss=1280 on both sides or Sync after panel update, then restart tunnel",
            )
        )
    if pulse.status == HpxPulseStatus.unhealthy:
        msg = (pulse.message or "").lower()
        if "silent" in msg:
            checks.append(
                PulseDiagCheck(
                    g,
                    "Root cause hint",
                    "fail",
                    pulse.message or "agent silent",
                    "Agent lost panel reachability or process died — re-join only if Tokens were regenerated",
                )
            )
        elif "forward" in msg or "443" in msg or "closed" in msg:
            checks.append(
                PulseDiagCheck(
                    g,
                    "Root cause hint",
                    "fail",
                    pulse.message or "forward path down",
                    "Control tunnel may be up but user port is closed — open Iran firewall for forward ports; ensure abroad backend listens",
                )
            )
        elif "cannot reach" in msg or "control" in msg:
            checks.append(
                PulseDiagCheck(
                    g,
                    "Root cause hint",
                    "fail",
                    pulse.message or "control path down",
                    "Abroad cannot dial Iran:control_port — check Iran public IP, tunnel port firewall, and that Iran agent is listening",
                )
            )

    stale_threshold = AGENT_STALE_SECONDS
    checks.append(
        PulseDiagCheck(
            g,
            "Watchdog",
            "info",
            f"agent stale after {stale_threshold}s · auto_heal={pulse.auto_heal_enabled} · last_heal={pulse.last_heal_action or '—'}",
        )
    )
    return checks


def diagnose_summary(checks: list[PulseDiagCheck]) -> dict[str, Any]:
    ok = sum(1 for c in checks if c.level == "ok")
    warn = sum(1 for c in checks if c.level == "warn")
    fail = sum(1 for c in checks if c.level == "fail")
    top_fail = next((c for c in checks if c.level == "fail"), None)
    return {
        "ok": ok,
        "warn": warn,
        "fail": fail,
        "healthy": fail == 0,
        "headline": top_fail.detail if top_fail else ("All critical checks passed" if warn == 0 else "Degraded — see warnings"),
        "primary_fix": top_fail.fix if top_fail else "",
        "checks": [asdict(c) for c in checks],
    }
