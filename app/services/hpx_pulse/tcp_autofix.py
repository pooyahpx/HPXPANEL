"""TCP-reverse autofix helpers for Pulse Diagnose agent."""

from __future__ import annotations

from typing import Any

from app.services.hpx_pulse.advisor import profile_meta

# Carriers where Iran↔abroad tunnel rides TCP (MSS/MTU stalls are common).
TCP_REVERSE_MODES = frozenset(
    {
        "reverse_stealth",
        "reverse_tcp",
        "reverse_tcpmux",
        "reverse_ws",
        "reverse_wss",
        "reverse_wssmux",
    }
)

EXTREME_STEALTH = "pulse-reverse-tcp-stealth-mtu-extreme"
EXTREME_TCP = "pulse-reverse-tcp-mtu-extreme"


def diag_has_stall(diag_report: Any) -> bool:
    """True if last agent probe reported stall_after_connect / TCP hang."""
    if not isinstance(diag_report, dict):
        return False

    def _side_stall(side: dict) -> bool:
        tcp = side.get("tcp") if isinstance(side.get("tcp"), dict) else {}
        for key in ("forward_exchange", "tls_via_iran"):
            item = tcp.get(key) if isinstance(tcp, dict) else None
            if isinstance(item, dict) and (item.get("stall") or "stall" in str(item.get("detail") or "").lower()):
                return True
        verdict = side.get("verdict") if isinstance(side.get("verdict"), dict) else {}
        summary = str(verdict.get("summary") or "").lower()
        return "stall" in summary

    sides = diag_report.get("sides")
    if isinstance(sides, dict):
        return any(isinstance(s, dict) and _side_stall(s) for s in sides.values())
    return _side_stall(diag_report)


def pick_tcp_extreme_profile(tunnel_mode: str | None, profile_id: str | None) -> str | None:
    """Return Extreme profile_id when pulse is on TCP reverse without Extreme MSS."""
    mode = (tunnel_mode or "").strip()
    if mode not in TCP_REVERSE_MODES:
        return None
    pid = (profile_id or "").strip()
    if "mtu-extreme" in pid:
        return None
    # Keep plain reverse_tcp on TCP Extreme (not Stealth) when already tcp carrier.
    if mode == "reverse_tcp" or pid in {"pulse-reverse-tcp", "pulse-reverse-tcp-mtu"}:
        return EXTREME_TCP
    return EXTREME_STEALTH


def should_autofix_tcp_extreme(pulse: Any) -> str | None:
    """
    Decide whether Diagnose should force TCP Extreme + Sync.

    Triggers: stall in last report, or TCP reverse still on a non-Extreme profile
    (plain Stealth / Safe MTU) — operator asked for aggressive TCP-reverse repair.
    """
    mode = getattr(pulse, "tunnel_mode", None)
    pid = getattr(pulse, "profile_id", None)
    target = pick_tcp_extreme_profile(mode, pid)
    if not target:
        return None
    # Always escalate TCP reverse on Diagnose when not already Extreme.
    # Stall makes it mandatory; without stall we still upgrade plain Stealth
    # because connect-OK / payload-fail is the common Iran path failure mode.
    return target


def extreme_profile_update(profile_id: str) -> dict[str, Any]:
    meta = profile_meta(profile_id)
    return {
        "profile_id": meta["profile_id"],
        "tunnel_mode": meta["tunnel_mode"],
        "carrier": meta.get("carrier"),
        "preset": meta["preset"],
    }
