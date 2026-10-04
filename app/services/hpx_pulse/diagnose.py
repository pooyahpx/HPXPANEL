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


def _checks_from_one_agent_diag(report: dict, side: str) -> list[PulseDiagCheck]:
    """Turn one side's agent probe JSON into Diagnose rows."""
    checks: list[PulseDiagCheck] = []
    g = f"Agent probe · {side or report.get('side') or '?'}"
    age = None
    ts = report.get("ts")
    if isinstance(ts, (int, float)):
        age = max(0, int(dt.now(UTC).timestamp() - ts))
    checks.append(
        PulseDiagCheck(
            g,
            "Report age",
            "ok" if age is not None and age < 120 else "warn",
            f"{age}s ago · host={report.get('host') or '—'} · engine={report.get('engine_version') or '—'}",
            "Click Diagnose again and wait ~10s for a fresh agent probe" if age is None or age >= 120 else "",
        )
    )

    for key, title in (
        ("tunnel_service", "Tunnel systemd"),
        ("mode", "Mode / side"),
        ("transport", "TOML transport"),
        ("orphan_tunnels", "Orphan tunnel units"),
        ("control_listen", "Control port listen (Iran)"),
        ("backend_listen", "Backend listen (abroad)"),
        ("xray", "Xray / core process"),
        ("mss", "MSS in TOML"),
    ):
        item = report.get(key)
        if not isinstance(item, dict):
            continue
        ok = bool(item.get("ok"))
        level: DiagLevel = "ok" if ok else "fail"
        if key in {"mss", "transport", "mode"} and not ok:
            level = "warn"
        if key == "mss" and not ok:
            level = "warn"
        checks.append(
            PulseDiagCheck(
                g,
                title,
                level,
                str(item.get("detail") or ("ok" if ok else "fail")),
                str(item.get("fix") or ""),
            )
        )
        # Nested Xray TLS local
        if key == "xray":
            tls_l = item.get("tls_local") if isinstance(item.get("tls_local"), dict) else None
            if tls_l:
                lok = bool(tls_l.get("ok"))
                checks.append(
                    PulseDiagCheck(
                        g,
                        "Xray TLS local",
                        "ok" if lok else "fail",
                        str(tls_l.get("detail") or ""),
                        str(tls_l.get("fix") or ""),
                    )
                )

    tcp = report.get("tcp") if isinstance(report.get("tcp"), dict) else {}
    for key, title in (
        ("control", "TCP → Iran control"),
        ("forward", "TCP → Iran forward"),
        ("forward_exchange", "TCP data after connect (MSS test)"),
        ("tls_via_iran", "TLS via Iran forward (Reality path)"),
    ):
        item = tcp.get(key) if isinstance(tcp, dict) else None
        if not isinstance(item, dict):
            continue
        state = item.get("state") or ("ok" if item.get("ok") else "fail")
        level = "ok" if state == "ok" else ("warn" if state == "warn" else "fail")
        if item.get("stall"):
            level = "fail"
        detail = str(item.get("detail") or state)
        fix = str(item.get("fix") or "")
        if item.get("stall"):
            # Panel Diagnose autofixes to TCP Extreme; text for second-click confirmation.
            fix = (
                "TCP connects then stalls on first bytes — classic MTU/MSS on TCP carrier. "
                "Diagnose auto-applies «TCP Extreme — Reverse Stealth (MSS 1000)» + Sync; "
                "wait ~20s and Diagnose again. Keep TCP — do not switch to KCP unless Extreme still fails."
            )
        checks.append(PulseDiagCheck(g, title, level, detail, fix))

    udp = report.get("udp") if isinstance(report.get("udp"), dict) else {}
    if isinstance(udp, dict) and udp.get("detail"):
        checks.append(
            PulseDiagCheck(
                g,
                "UDP note",
                "info",
                str(udp.get("detail")),
                str(udp.get("fix") or ""),
            )
        )

    verdict = report.get("verdict")
    if isinstance(verdict, dict) and verdict.get("summary"):
        level = "fail" if verdict.get("level") == "fail" else ("warn" if verdict.get("level") == "warn" else "info")
        checks.append(
            PulseDiagCheck(
                g,
                "Verdict",
                level,
                str(verdict.get("summary")),
                str(verdict.get("fix") or ""),
            )
        )
    return checks


def _checks_from_agent_diag(pulse: HpxPulse) -> list[PulseDiagCheck]:
    """Turn last agent probe JSON into Diagnose rows (supports multi-side reports)."""
    report = pulse.diag_report if isinstance(pulse.diag_report, dict) else None
    if not report:
        return []
    sides = report.get("sides")
    if isinstance(sides, dict) and sides:
        checks: list[PulseDiagCheck] = []
        # Abroad path probes first — they catch MSS stalls.
        for side_name in ("abroad", "iran"):
            side_report = sides.get(side_name)
            if isinstance(side_report, dict):
                checks.extend(_checks_from_one_agent_diag(side_report, side_name))
        for side_name, side_report in sides.items():
            if side_name in {"abroad", "iran"}:
                continue
            if isinstance(side_report, dict):
                checks.extend(_checks_from_one_agent_diag(side_report, str(side_name)))
        return checks
    return _checks_from_one_agent_diag(report, str(report.get("side") or "?"))


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
            ""
            if pulse.status == HpxPulseStatus.running
            else "Open Diagnose, wait 10s, open again — agents push live TCP probes",
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
            "Set both public IPs and a free control port"
            if not (pulse.iran_public_ip and pulse.abroad_public_ip)
            else "",
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
                    f"On {side} VPS: sudo hpx-pulse-agent sync && sudo hpx-pulse-agent ping",
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

    if pulse.latency_ms is None:
        if is_reverse:
            checks.append(
                PulseDiagCheck(
                    g,
                    "Live ping",
                    "fail",
                    "no RTT — abroad cannot TCP-reach Iran control or forward port",
                    "Iran firewall TCP for control+forwards; abroad Xray on 127.0.0.1:<forward>",
                )
            )
        else:
            checks.append(
                PulseDiagCheck(
                    g,
                    "Live ping",
                    "warn",
                    "no ICMP RTT on L3 peer (ICMP often blocked) — not tunnel health",
                    "Check bp0 + tunnel service",
                )
            )
    else:
        level: DiagLevel = "ok"
        fix = ""
        msg_l = (pulse.message or "").lower()
        if pulse.latency_ms > 300:
            level = "warn"
            fix = "High RTT — try preset speed or closer abroad VPS"
        if "control ok" in msg_l and ("closed" in msg_l or "forward" in msg_l):
            level = "fail"
            fix = "Control up, user TCP port dead — Iran forward firewall / abroad backend"
        detail = f"{pulse.latency_ms:.1f} ms (TCP path RTT)"
        if pulse.message:
            detail += f" — {pulse.message}"
        checks.append(PulseDiagCheck(g, "Live ping", level, detail, fix))

    checks.extend(_checks_from_agent_diag(pulse))

    if is_reverse:
        tcp_modes = {
            "reverse_stealth",
            "reverse_tcp",
            "reverse_tcpmux",
            "reverse_ws",
            "reverse_wss",
            "reverse_wssmux",
        }
        if mode in tcp_modes:
            checks.append(
                PulseDiagCheck(
                    g,
                    "TCP reverse path",
                    "info",
                    "Tunnel carrier is TCP/Stealth/WSS — user Reality still lands on Iran:443. "
                    "If ping is green but TLS hangs: MSS/MTU stall (Diagnose → TCP Extreme autofix).",
                    "Click Diagnose — panel upgrades to TCP Extreme (mss=1000), rewrites Hosts "
                    "that point at abroad IP → Iran IP, then agents Sync + probe.",
                )
            )
        else:
            checks.append(
                PulseDiagCheck(
                    g,
                    "UDP carrier note",
                    "info",
                    "Carrier is UDP-family (KCP/QUIC/UDP) — user TCP still uses Iran forwards.",
                    "For TCP-only repair: Edit → TCP Extreme Stealth → Save → Sync.",
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
                    "Re-join only if Tokens were regenerated",
                )
            )
        elif "forward" in msg or "443" in msg or "closed" in msg:
            checks.append(
                PulseDiagCheck(
                    g,
                    "Root cause hint",
                    "fail",
                    pulse.message or "forward path down",
                    "Open Iran forward ports; ensure abroad backend listens",
                )
            )
        elif "cannot reach" in msg or "control" in msg:
            checks.append(
                PulseDiagCheck(
                    g,
                    "Root cause hint",
                    "fail",
                    pulse.message or "control path down",
                    "Abroad cannot dial Iran:control_port",
                )
            )

    checks.append(
        PulseDiagCheck(
            g,
            "Watchdog",
            "info",
            f"agent stale after {AGENT_STALE_SECONDS}s · auto_heal={pulse.auto_heal_enabled} · last_heal={pulse.last_heal_action or '—'}",
        )
    )
    return checks


def checks_from_linked_hosts(hits: list[Any]) -> list[PulseDiagCheck]:
    """Panel Host rows that reference this Pulse's Iran/abroad public IPs."""
    checks: list[PulseDiagCheck] = []
    g = "Panel configs · Hosts"
    if not hits:
        checks.append(
            PulseDiagCheck(
                g,
                "Related Hosts",
                "warn",
                "No Host address matches this Pulse Iran/abroad IP — subscription may still point elsewhere",
                "Hosts → set address to Iran public IP so clients enter the reverse TCP forward",
            )
        )
        return checks
    for hit in hits:
        issue = getattr(hit, "issue", "")
        if issue == "abroad_ip":
            level: DiagLevel = "fail"
        elif issue == "mixed":
            level = "fail"
        elif issue == "ok_iran":
            level = "ok"
        else:
            level = "info"
        fix = ""
        if issue in {"abroad_ip", "mixed"}:
            fix = (
                "Diagnose autofix rewrites abroad IP → Iran IP on this Host. "
                "Re-fetch subscription on the client after fix."
            )
        checks.append(
            PulseDiagCheck(
                g,
                f"Host #{getattr(hit, 'host_id', '?')} {getattr(hit, 'remark', '')}".strip(),
                level,
                getattr(hit, "detail", "") or str(getattr(hit, "addresses", [])),
                fix,
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
        "headline": top_fail.detail
        if top_fail
        else ("All critical checks passed" if warn == 0 else "Degraded — see warnings"),
        "primary_fix": top_fail.fix if top_fail else "",
        "checks": [asdict(c) for c in checks],
    }
