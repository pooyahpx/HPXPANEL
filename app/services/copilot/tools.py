from __future__ import annotations

import json
from typing import Any

from app.db import AsyncSession
from app.models.admin import AdminDetails
from app.models.hpx_tunnel import HpxTunnelsQuery
from app.operation import OperatorType
from app.operation.hpx_pulse import HpxPulseOperation
from app.operation.hpx_tunnel import HpxTunnelOperation
from app.operation.permissions import PermissionDenied, enforce_permission
from app.services.copilot.context import diagnose_pulse

_pulse_op_instance: HpxPulseOperation | None = None
_tunnel_op_instance: HpxTunnelOperation | None = None


def _get_pulse_op() -> HpxPulseOperation:
    global _pulse_op_instance
    if _pulse_op_instance is None:
        _pulse_op_instance = HpxPulseOperation(operator_type=OperatorType.API)
    return _pulse_op_instance


def _get_tunnel_op() -> HpxTunnelOperation:
    global _tunnel_op_instance
    if _tunnel_op_instance is None:
        _tunnel_op_instance = HpxTunnelOperation(operator_type=OperatorType.API)
    return _tunnel_op_instance

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_hpx_pulses",
            "description": "List HPX Pulse smart tunnels with agent connection and status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max items (1-20)", "default": 10},
                    "name": {"type": "string", "description": "Optional name filter"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_hpx_pulse",
            "description": "Get one HPX Pulse by id with full details.",
            "parameters": {
                "type": "object",
                "properties": {"pulse_id": {"type": "integer"}},
                "required": ["pulse_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "diagnose_hpx_pulse",
            "description": "Run rule-based health diagnosis for one HPX Pulse.",
            "parameters": {
                "type": "object",
                "properties": {"pulse_id": {"type": "integer"}},
                "required": ["pulse_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sync_hpx_pulse",
            "description": "Queue config sync/restart for connected HPX Pulse agents.",
            "parameters": {
                "type": "object",
                "properties": {"pulse_id": {"type": "integer"}},
                "required": ["pulse_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_hpx_tunnels",
            "description": "List HPX ICMP tunnels (Iran/foreign Docker tunnels).",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max items (1-20)", "default": 10},
                    "name": {"type": "string", "description": "Optional name filter"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_hpx_tunnel",
            "description": "Get one HPX ICMP tunnel by id.",
            "parameters": {
                "type": "object",
                "properties": {"tunnel_id": {"type": "integer"}},
                "required": ["tunnel_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "restart_hpx_tunnel",
            "description": "Restart an HPX ICMP tunnel container.",
            "parameters": {
                "type": "object",
                "properties": {"tunnel_id": {"type": "integer"}},
                "required": ["tunnel_id"],
            },
        },
    },
]


def _pulse_summary(pulse) -> dict[str, Any]:
    return {
        "id": pulse.id,
        "name": pulse.name,
        "status": pulse.status,
        "enabled": pulse.enabled,
        "profile_id": pulse.profile_id,
        "iran_public_ip": pulse.iran_public_ip,
        "abroad_public_ip": pulse.abroad_public_ip,
        "iran_claimed": pulse.iran_claimed,
        "abroad_claimed": pulse.abroad_claimed,
        "iran_agent_host": pulse.iran_agent_host,
        "abroad_agent_host": pulse.abroad_agent_host,
        "iran_agent_last_seen": pulse.iran_agent_last_seen.isoformat() if pulse.iran_agent_last_seen else None,
        "abroad_agent_last_seen": pulse.abroad_agent_last_seen.isoformat() if pulse.abroad_agent_last_seen else None,
        "latency_ms": pulse.latency_ms,
        "packet_loss_pct": pulse.packet_loss_pct,
        "message": pulse.message,
        "port_forwards": pulse.port_forwards,
    }


def _tunnel_summary(tunnel) -> dict[str, Any]:
    return {
        "id": tunnel.id,
        "name": tunnel.name,
        "role": tunnel.role,
        "status": tunnel.status,
        "enabled": tunnel.enabled,
        "remote_ip": tunnel.remote_ip,
        "agent_claimed": tunnel.agent_claimed,
        "agent_host": tunnel.agent_host,
        "agent_last_seen": tunnel.agent_last_seen.isoformat() if tunnel.agent_last_seen else None,
        "latency_ms": tunnel.latency_ms,
        "message": tunnel.message,
    }


async def execute_tool(
    db: AsyncSession,
    *,
    admin: AdminDetails,
    name: str,
    arguments: dict[str, Any],
) -> tuple[dict[str, Any], str | None]:
    """Run a copilot tool. Returns (result, action_label)."""
    try:
        if name == "list_hpx_pulses":
            enforce_permission(admin, "hpx_pulse", "read")
            limit = max(1, min(int(arguments.get("limit") or 10), 20))
            resp = await _get_pulse_op().list_pulses(
                db, admin=admin, offset=0, limit=limit, name=arguments.get("name")
            )
            return {"total": resp.total, "pulses": [_pulse_summary(p) for p in resp.pulses]}, f"Listed {len(resp.pulses)} pulse(s)"

        if name == "get_hpx_pulse":
            enforce_permission(admin, "hpx_pulse", "read")
            pulse = await _get_pulse_op().get_pulse(db, admin=admin, pulse_id=int(arguments["pulse_id"]))
            return _pulse_summary(pulse), f"Fetched pulse #{pulse.id}"

        if name == "diagnose_hpx_pulse":
            enforce_permission(admin, "hpx_pulse", "read")
            pulse = await _get_pulse_op().get_pulse(db, admin=admin, pulse_id=int(arguments["pulse_id"]))
            return diagnose_pulse(pulse), f"Diagnosed pulse #{pulse.id}"

        if name == "sync_hpx_pulse":
            enforce_permission(admin, "hpx_pulse", "update")
            result = await _get_pulse_op().sync_pulse(db, admin=admin, pulse_id=int(arguments["pulse_id"]))
            return {
                "pulse_id": result.pulse.id,
                "message": result.message,
                "status": result.pulse.status,
            }, f"Synced pulse #{result.pulse.id}"

        if name == "list_hpx_tunnels":
            enforce_permission(admin, "hpx_tunnels", "read")
            limit = max(1, min(int(arguments.get("limit") or 10), 20))
            query = HpxTunnelsQuery(offset=0, limit=limit, name=arguments.get("name"))
            resp = await _get_tunnel_op().list_tunnels(db, admin=admin, query=query)
            return {"total": resp.total, "tunnels": [_tunnel_summary(t) for t in resp.tunnels]}, f"Listed {len(resp.tunnels)} tunnel(s)"

        if name == "get_hpx_tunnel":
            enforce_permission(admin, "hpx_tunnels", "read")
            tunnel = await _get_tunnel_op().get_tunnel(db, admin=admin, tunnel_id=int(arguments["tunnel_id"]))
            return _tunnel_summary(tunnel), f"Fetched tunnel #{tunnel.id}"

        if name == "restart_hpx_tunnel":
            enforce_permission(admin, "hpx_tunnels", "restart")
            result = await _get_tunnel_op().restart_tunnel_action(db, admin=admin, tunnel_id=int(arguments["tunnel_id"]))
            return {"tunnel_id": result.tunnel.id, "status": result.tunnel.status, "message": result.message}, (
                f"Restarted tunnel #{result.tunnel.id}"
            )

        return {"error": f"Unknown tool: {name}"}, None
    except PermissionDenied as exc:
        return {"error": str(exc)}, None
    except KeyError as exc:
        return {"error": f"Missing argument: {exc}"}, None
    except Exception as exc:  # noqa: BLE001 — surface tool errors to the model
        return {"error": str(exc)}, None


def tool_result_content(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, default=str)
