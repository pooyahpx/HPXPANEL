from __future__ import annotations

import json
from typing import Any

from app.db import AsyncSession
from app.models.admin import AdminDetails
from app.models.hpx_tunnel import HpxTunnelsQuery
from app.operation import OperatorType
from app.operation.hpx_pulse import HpxPulseOperation
from app.operation.hpx_tunnel import HpxTunnelOperation
from app.operation.node import NodeOperation
from app.operation.user import UserOperation
from app.operation.permissions import PermissionDenied, enforce_permission
from app.models.node import NodeListQuery, NodeResponse
from app.models.user import UserListQuery
from app.services.copilot.context import diagnose_pulse
from app.services.copilot.host_import import import_proxy_link as run_proxy_link_import, list_core_inbound_options
from app.services.copilot.panel_ops import (
    build_panel_health,
    diagnose_node_live,
    node_summary,
    user_summary,
)

_pulse_op_instance: HpxPulseOperation | None = None
_tunnel_op_instance: HpxTunnelOperation | None = None
_node_op_instance: NodeOperation | None = None
_user_op_instance: UserOperation | None = None


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


def _get_node_op() -> NodeOperation:
    global _node_op_instance
    if _node_op_instance is None:
        _node_op_instance = NodeOperation(operator_type=OperatorType.API)
    return _node_op_instance


def _get_user_op() -> UserOperation:
    global _user_op_instance
    if _user_op_instance is None:
        _user_op_instance = UserOperation(operator_type=OperatorType.API)
    return _user_op_instance


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "overview_hpx_tunnel_systems",
            "description": (
                "List ALL tunnel products in HPXPANEL in one call. Use this when the user asks about "
                "'tunnels', 'تونل', HPX Pulse status, or a general tunnel health review. "
                "Returns hpx_pulse (reverse tunnel advisor, Iran+abroad agents) AND hpx_icmp "
                "(separate ICMP Docker tunnels). Do NOT treat empty ICMP as 'no tunnels' if Pulse exists."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max items per product (1-20)", "default": 10},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "panel_health",
            "description": (
                "Panel health snapshot: version, CPU/RAM/disk, user counts, NATS workers, "
                "node status summary, and recent node errors. Use for general panel troubleshooting."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_nodes",
            "description": "List HPX edge nodes (Xray/VPN agents) with connection status and traffic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max items (1-20)", "default": 10},
                    "search": {"type": "string", "description": "Optional name/address search"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_node",
            "description": "Get one edge node by id with full details.",
            "parameters": {
                "type": "object",
                "properties": {"node_id": {"type": "integer"}},
                "required": ["node_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "diagnose_node",
            "description": (
                "Diagnose an edge node: DB status, live CPU/RAM, outbound latency, connection issues. "
                "Suggests sync/reconnect steps. Requires node_id from list_nodes."
            ),
            "parameters": {
                "type": "object",
                "properties": {"node_id": {"type": "integer"}},
                "required": ["node_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_users",
            "description": "List panel users with traffic, limits, expiry, and status (subscription troubleshooting).",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max items (1-20)", "default": 10},
                    "search": {"type": "string", "description": "Search username"},
                    "username": {"type": "string", "description": "Exact username filter"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user",
            "description": "Get one user by id — traffic, data_limit, expire, groups, online_at, limits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer"},
                    "include_subscription_url": {"type": "boolean", "default": False},
                },
                "required": ["user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_hpx_pulses",
            "description": (
                "List HPX Pulse tunnels only — the reverse-tunnel advisor (Iran + Abroad agents, "
                "profiles like stealth/TCP/WSS). NOT the ICMP tunnel product. "
                "Prefer overview_hpx_tunnel_systems when the user says 'tunnel' generically."
            ),
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
            "description": (
                "List HPX ICMP tunnels only — ChaCha ping tunnels in Docker (Iran/foreign roles). "
                "This is NOT HPX Pulse. If the user asked about Pulse or tunnels in general, "
                "also call overview_hpx_tunnel_systems or list_hpx_pulses."
            ),
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
    {
        "type": "function",
        "function": {
            "name": "list_core_inbounds",
            "description": "List Xray inbound tags from loaded core configs (for linking a Host).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "import_proxy_link",
            "description": (
                "Parse a client share link (vless://, vmess://, trojan://, ss://) and create a HPXPANEL Host. "
                "By default also creates a matching Xray inbound in the core when none exists (create_inbound_if_missing). "
                "Always preview first with confirm=false, then create with confirm=true after the admin agrees. "
                "inbound_tag is optional — omit it to auto-match or auto-create from the link. "
                "Optional create_user with username + group_ids."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "link": {"type": "string", "description": "Full share link URI"},
                    "inbound_tag": {
                        "type": "string",
                        "description": "Optional existing inbound tag; leave empty to auto-match/create from link",
                    },
                    "core_id": {
                        "type": "integer",
                        "description": "Optional Xray core id (defaults to first Xray core)",
                    },
                    "create_inbound_if_missing": {
                        "type": "boolean",
                        "description": "Create a matching inbound in the core when none exists",
                        "default": True,
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "false = preview only, true = create inbound (if needed) and host",
                        "default": False,
                    },
                    "remark_override": {"type": "string", "description": "Optional host remark override"},
                    "create_user": {
                        "type": "boolean",
                        "description": "Also create a user with UUID/password from the link",
                        "default": False,
                    },
                    "username": {"type": "string"},
                    "group_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Group IDs required when create_user=true",
                    },
                },
                "required": ["link"],
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


async def _overview_hpx_tunnel_systems(
    db: AsyncSession,
    *,
    admin: AdminDetails,
    limit: int,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "note": (
            "HPXPANEL has two tunnel products: HPX Pulse (reverse advisor) and HPX ICMP (ping Docker). "
            "They are separate — report both when reviewing tunnels."
        ),
        "hpx_pulse": {
            "product": "HPX Pulse — reverse tunnel advisor (Iran + Abroad agents)",
            "total": 0,
            "items": [],
        },
        "hpx_icmp": {
            "product": "HPX ICMP — ChaCha ping Docker tunnels",
            "total": 0,
            "items": [],
        },
    }

    try:
        enforce_permission(admin, "hpx_pulse", "read")
        pulse_resp = await _get_pulse_op().list_pulses(db, admin=admin, offset=0, limit=limit)
        result["hpx_pulse"]["total"] = pulse_resp.total
        result["hpx_pulse"]["items"] = [_pulse_summary(p) for p in pulse_resp.pulses]
    except PermissionDenied:
        result["hpx_pulse"]["permission_denied"] = True

    try:
        enforce_permission(admin, "hpx_tunnels", "read")
        icmp_query = HpxTunnelsQuery(offset=0, limit=limit)
        icmp_resp = await _get_tunnel_op().list_tunnels(db, admin=admin, query=icmp_query)
        result["hpx_icmp"]["total"] = icmp_resp.total
        result["hpx_icmp"]["items"] = [_tunnel_summary(t) for t in icmp_resp.tunnels]
    except PermissionDenied:
        result["hpx_icmp"]["permission_denied"] = True

    return result


async def execute_tool(
    db: AsyncSession,
    *,
    admin: AdminDetails,
    name: str,
    arguments: dict[str, Any],
) -> tuple[dict[str, Any], str | None]:
    """Run a copilot tool. Returns (result, action_label)."""
    try:
        if name == "overview_hpx_tunnel_systems":
            limit = max(1, min(int(arguments.get("limit") or 10), 20))
            overview = await _overview_hpx_tunnel_systems(db, admin=admin, limit=limit)
            pulse_n = len(overview["hpx_pulse"].get("items") or [])
            icmp_n = len(overview["hpx_icmp"].get("items") or [])
            return overview, f"Overview: {pulse_n} Pulse(s), {icmp_n} ICMP tunnel(s)"

        if name == "panel_health":
            enforce_permission(admin, "system", "read")
            health = await build_panel_health(db, admin=admin)
            return health, "Panel health snapshot"

        if name == "list_nodes":
            enforce_permission(admin, "nodes", "read")
            limit = max(1, min(int(arguments.get("limit") or 10), 20))
            query = NodeListQuery(offset=0, limit=limit, search=arguments.get("search") or None)
            resp = await _get_node_op().get_db_nodes(db, query)
            return {
                "total": resp.total,
                "nodes": [node_summary(n) for n in resp.nodes],
            }, f"Listed {len(resp.nodes)} node(s)"

        if name == "get_node":
            enforce_permission(admin, "nodes", "read")
            db_node = await _get_node_op().get_validated_node(db, int(arguments["node_id"]))
            node = NodeResponse.model_validate(db_node)
            return node_summary(node), f"Fetched node #{node.id}"

        if name == "diagnose_node":
            enforce_permission(admin, "nodes", "read")
            diagnosis = await diagnose_node_live(db, admin=admin, node_id=int(arguments["node_id"]))
            return diagnosis, f"Diagnosed node #{arguments['node_id']}"

        if name == "list_users":
            enforce_permission(admin, "users", "read")
            limit = max(1, min(int(arguments.get("limit") or 10), 20))
            username = arguments.get("username")
            query = UserListQuery(
                offset=0,
                limit=limit,
                search=arguments.get("search") or None,
                username=[username] if username else None,
            )
            resp = await _get_user_op().get_users(db, admin=admin, query=query)
            return {
                "total": resp.total,
                "users": [user_summary(u) for u in resp.users],
            }, f"Listed {len(resp.users)} user(s)"

        if name == "get_user":
            enforce_permission(admin, "users", "read")
            user = await _get_user_op().get_user_by_id(db, int(arguments["user_id"]), admin)
            return user_summary(user, include_subscription_url=bool(arguments.get("include_subscription_url"))), (
                f"Fetched user {user.username}"
            )

        if name == "list_hpx_pulses":
            enforce_permission(admin, "hpx_pulse", "read")
            limit = max(1, min(int(arguments.get("limit") or 10), 20))
            resp = await _get_pulse_op().list_pulses(db, admin=admin, offset=0, limit=limit, name=arguments.get("name"))
            return {
                "total": resp.total,
                "pulses": [_pulse_summary(p) for p in resp.pulses],
            }, f"Listed {len(resp.pulses)} pulse(s)"

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
            return {
                "total": resp.total,
                "tunnels": [_tunnel_summary(t) for t in resp.tunnels],
            }, f"Listed {len(resp.tunnels)} tunnel(s)"

        if name == "get_hpx_tunnel":
            enforce_permission(admin, "hpx_tunnels", "read")
            tunnel = await _get_tunnel_op().get_tunnel(db, admin=admin, tunnel_id=int(arguments["tunnel_id"]))
            return _tunnel_summary(tunnel), f"Fetched tunnel #{tunnel.id}"

        if name == "restart_hpx_tunnel":
            enforce_permission(admin, "hpx_tunnels", "restart")
            result = await _get_tunnel_op().restart_tunnel_action(
                db, admin=admin, tunnel_id=int(arguments["tunnel_id"])
            )
            return {"tunnel_id": result.tunnel.id, "status": result.tunnel.status, "message": result.message}, (
                f"Restarted tunnel #{result.tunnel.id}"
            )

        if name == "list_core_inbounds":
            enforce_permission(admin, "hosts", "read")
            inbounds = await list_core_inbound_options()
            return {"total": len(inbounds), "inbounds": inbounds}, f"Listed {len(inbounds)} inbound(s)"

        if name == "import_proxy_link":
            create_inbound = bool(arguments.get("create_inbound_if_missing", True))
            if arguments.get("confirm"):
                enforce_permission(admin, "hosts", "create")
                if create_inbound:
                    enforce_permission(admin, "cores", "update")
                if arguments.get("create_user"):
                    enforce_permission(admin, "users", "create")
            else:
                enforce_permission(admin, "hosts", "read")

            group_ids_raw = arguments.get("group_ids") or []
            group_ids = [int(item) for item in group_ids_raw] if group_ids_raw else None
            core_id_raw = arguments.get("core_id")
            core_id = int(core_id_raw) if core_id_raw not in (None, "") else None

            result = await run_proxy_link_import(
                db,
                admin=admin,
                link=str(arguments.get("link") or ""),
                inbound_tag=str(arguments.get("inbound_tag") or ""),
                confirm=bool(arguments.get("confirm")),
                remark_override=arguments.get("remark_override"),
                create_user=bool(arguments.get("create_user")),
                username=arguments.get("username"),
                group_ids=group_ids,
                core_id=core_id,
                create_inbound_if_missing=create_inbound,
            )
            if arguments.get("confirm") and result.get("host_id"):
                label = f"Imported host #{result['host_id']}"
                if result.get("username"):
                    label += f" + user {result['username']}"
                return result, label
            return result, "Previewed proxy link import"

        return {"error": f"Unknown tool: {name}"}, None
    except PermissionDenied as exc:
        return {"error": str(exc)}, None
    except KeyError as exc:
        return {"error": f"Missing argument: {exc}"}, None
    except Exception as exc:
        return {"error": str(exc)}, None


def tool_result_content(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, default=str)
