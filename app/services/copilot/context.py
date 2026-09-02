from __future__ import annotations

from datetime import UTC, datetime as dt

from sqlalchemy import func, select

from app import __version__
from app.db import AsyncSession
from app.db.crud.hpx_pulse import get_hpx_pulses
from app.db.crud.hpx_tunnel import get_hpx_tunnels
from app.db.crud.user import get_users_count
from app.db.models import Node
from app.models.admin import AdminDetails
from app.models.hpx_pulse import HpxPulseResponse
from app.operation.permissions import enforce_permission


def _age_seconds(ts: dt | None) -> int | None:
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return max(0, int((dt.now(UTC) - ts.astimezone(UTC)).total_seconds()))


def diagnose_pulse(pulse: HpxPulseResponse) -> dict:
    issues: list[str] = []
    suggestions: list[str] = []

    if not pulse.iran_claimed:
        issues.append("Iran agent is not connected")
        suggestions.append("Run the Iran join command on the Iran server and wait for heartbeat")
    if not pulse.abroad_claimed:
        issues.append("Abroad agent is not connected")
        suggestions.append("Run the abroad join command on the foreign server")

    if pulse.iran_claimed and pulse.iran_agent_last_seen is not None:
        age = _age_seconds(pulse.iran_agent_last_seen)
        if age is not None and age > 180:
            issues.append(f"Iran agent heartbeat is stale ({age}s ago)")
            suggestions.append("Check hpx-pulse-agent service on Iran server: systemctl status hpx-pulse-agent")

    if pulse.abroad_claimed and pulse.abroad_agent_last_seen is not None:
        age = _age_seconds(pulse.abroad_agent_last_seen)
        if age is not None and age > 180:
            issues.append(f"Abroad agent heartbeat is stale ({age}s ago)")
            suggestions.append("Check hpx-pulse-agent service on abroad server")

    if pulse.status in {"error", "unhealthy", "partial"}:
        issues.append(f"Pulse status is {pulse.status}")
        suggestions.append("Use Sync on the pulse card or run: sudo hpx-pulse-agent install-engine --force")

    if pulse.message:
        issues.append(f"Panel message: {pulse.message}")

    if pulse.packet_loss_pct is not None and pulse.packet_loss_pct > 5:
        issues.append(f"High packet loss: {pulse.packet_loss_pct}%")
        suggestions.append("Try a different profile or check UDP reachability between Iran and abroad")

    return {
        "pulse_id": pulse.id,
        "name": pulse.name,
        "status": pulse.status,
        "issues": issues,
        "suggestions": suggestions,
        "healthy": not issues,
    }


async def build_panel_snapshot(
    db: AsyncSession,
    *,
    admin: AdminDetails,
    page_path: str | None,
) -> dict:
    snapshot: dict = {
        "panel_version": __version__,
        "admin_username": admin.username,
        "page_path": page_path or "/",
        "is_owner": admin.is_owner,
    }

    try:
        enforce_permission(admin, "system", "read")
        snapshot["users_total"] = await get_users_count(db)
        snapshot["nodes_total"] = int((await db.execute(select(func.count(Node.id)))).scalar_one() or 0)
    except Exception:
        pass

    try:
        enforce_permission(admin, "hpx_pulse", "read")
        pulses, pulse_total = await get_hpx_pulses(db, offset=0, limit=5)
        snapshot["hpx_pulses_total"] = pulse_total
        snapshot["hpx_pulse_preview"] = [
            {
                "id": p.id,
                "name": p.name,
                "status": p.status,
                "iran_claimed": p.iran_claimed,
                "abroad_claimed": p.abroad_claimed,
            }
            for p in pulses
        ]
    except Exception:
        pass

    try:
        enforce_permission(admin, "hpx_tunnels", "read")
        _, tunnel_total = await get_hpx_tunnels(db, offset=0, limit=1)
        snapshot["hpx_icmp_tunnels_total"] = tunnel_total
    except Exception:
        pass

    snapshot["tunnel_products"] = {
        "hpx_pulse": "Reverse tunnel advisor — Iran + Abroad agents (NOT ICMP)",
        "hpx_icmp": "ICMP ChaCha Docker tunnels — separate product",
    }

    page = (page_path or "").lower()
    if "pulse" in page:
        snapshot["page_hint"] = "User is on HPX Pulse UI — prioritize Pulse tools and status."
    elif "icmp" in page or "hpx-tunnel" in page or "hpx_tunnel" in page:
        snapshot["page_hint"] = "User is on HPX ICMP UI — ICMP tunnels; Pulse is a different product."
    elif "node" in page:
        snapshot["page_hint"] = "User is on Nodes UI — use list_nodes / diagnose_node."
    elif "user" in page:
        snapshot["page_hint"] = "User is on Users UI — use list_users / get_user for subscription issues."

    return snapshot
