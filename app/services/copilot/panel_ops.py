from __future__ import annotations

import asyncio
import time
from collections import Counter
from typing import Any

from app.db import AsyncSession
from app.db.models import NodeStatus
from app.models.admin import AdminDetails
from app.models.node import NodeListQuery, NodeResponse
from app.models.system import WorkerHealth, WorkersHealth
from app.models.user import UserListQuery, UserNotificationResponse
from app.nats import is_nats_enabled
from app.nats.node_rpc import node_nats_client
from app.nats.scheduler_rpc import scheduler_nats_client
from app.operation import OperatorType
from app.operation.node import NodeOperation
from app.operation.permissions import PermissionDenied, enforce_permission
from app.operation.system import SystemOperation


async def _measure_worker_health(request_coro) -> WorkerHealth:
    start = time.monotonic()
    try:
        await request_coro
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return WorkerHealth(status="ok", response_time_ms=elapsed_ms)
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        error_msg = str(exc) or exc.__class__.__name__
        return WorkerHealth(status="down", response_time_ms=elapsed_ms, error=error_msg)


async def get_workers_health() -> WorkersHealth:
    if not is_nats_enabled():
        disabled = WorkerHealth(status="disabled")
        return WorkersHealth(scheduler=disabled, node=disabled)

    timeout = 5.0
    scheduler_task = _measure_worker_health(scheduler_nats_client.request("health_check", {}, timeout))
    node_task = _measure_worker_health(node_nats_client.request("health_check", {}, timeout))
    scheduler_health, node_health = await asyncio.gather(scheduler_task, node_task)
    return WorkersHealth(scheduler=scheduler_health, node=node_health)


def node_summary(node: NodeResponse) -> dict[str, Any]:
    status = node.status.value if hasattr(node.status, "value") else str(node.status)
    return {
        "id": node.id,
        "name": node.name,
        "status": status,
        "message": node.message,
        "address": node.address,
        "port": node.port,
        "api_port": node.api_port,
        "connection_type": str(node.connection_type),
        "core_config_id": node.core_config_id,
        "xray_version": node.xray_version,
        "node_version": node.node_version,
        "uplink": node.uplink,
        "downlink": node.downlink,
        "data_limit": node.data_limit,
    }


def user_summary(user: UserNotificationResponse, *, include_subscription_url: bool = False) -> dict[str, Any]:
    status = user.status.value if hasattr(user.status, "value") else str(user.status)
    expire = user.expire
    if hasattr(expire, "isoformat"):
        expire = expire.isoformat()
    summary: dict[str, Any] = {
        "id": user.id,
        "username": user.username,
        "status": status,
        "used_traffic": user.used_traffic,
        "lifetime_used_traffic": user.lifetime_used_traffic,
        "data_limit": user.data_limit,
        "expire": expire,
        "online_at": user.online_at.isoformat() if user.online_at else None,
        "group_names": user.group_names or [],
        "owner": user.admin.username if user.admin else None,
        "note": user.note,
        "hwid_limit": user.hwid_limit,
        "ip_limit": user.ip_limit,
    }
    if user.group_quotas:
        summary["group_quotas"] = [
            {
                "group_name": q.get("group_name") if isinstance(q, dict) else getattr(q, "group_name", None),
                "data_limit": q.get("data_limit") if isinstance(q, dict) else getattr(q, "data_limit", None),
                "used_traffic": q.get("used_traffic") if isinstance(q, dict) else getattr(q, "used_traffic", None),
                "is_limited": q.get("is_limited") if isinstance(q, dict) else getattr(q, "is_limited", None),
            }
            for q in user.group_quotas
        ]
    if include_subscription_url and user.subscription_url:
        summary["subscription_url"] = user.subscription_url
    return summary


def diagnose_node_record(
    node: NodeResponse,
    *,
    realtime: dict[str, Any] | None = None,
    outbounds: list[dict[str, Any]] | None = None,
    stats_error: str | None = None,
) -> dict[str, Any]:
    status = node.status.value if hasattr(node.status, "value") else str(node.status)
    issues: list[str] = []
    suggestions: list[str] = []

    if status == NodeStatus.error.value:
        issues.append(f"Node status is error: {node.message or 'no details'}")
        suggestions.append("Check node container logs, API key, Server CA, and firewall on ports")
        suggestions.append("Try Sync users on the node card in HPXPANEL → Nodes")
    elif status == NodeStatus.connecting.value:
        issues.append("Node is still connecting")
        suggestions.append("Wait a minute, then re-check. Verify address/port and node agent is running")
    elif status == NodeStatus.disabled.value:
        issues.append("Node is disabled in the panel")
        suggestions.append("Enable the node in HPXPANEL → Nodes if it should be active")
    elif status == NodeStatus.limited.value:
        issues.append("Node hit its data limit")
        suggestions.append("Raise node data_limit or reset node usage")

    if node.message and status != NodeStatus.error.value:
        issues.append(f"Panel message: {node.message}")

    if stats_error:
        issues.append(f"Live node API probe failed: {stats_error}")
        suggestions.append("Verify gRPC/API port, API key, and that hpx-node container is running (hpxnode on server)")

    if realtime is None and not stats_error:
        issues.append("No realtime stats returned from node")
        suggestions.append("Node may be unreachable — check connection from panel to node API port")

    if realtime:
        if realtime.get("cpu_usage", 0) > 90:
            issues.append(f"High CPU on node: {realtime['cpu_usage']}%")
        mem_total = realtime.get("mem_total") or 0
        mem_used = realtime.get("mem_used") or 0
        if mem_total and mem_used / mem_total > 0.9:
            issues.append("Node memory usage above 90%")

    dead_outbounds: list[str] = []
    if outbounds:
        for item in outbounds:
            if not item.get("alive"):
                dead_outbounds.append(str(item.get("name") or "unknown"))
        if dead_outbounds:
            issues.append(f"Dead/unreachable outbounds: {', '.join(dead_outbounds[:5])}")
            suggestions.append("Check Xray outbound config and upstream connectivity on the node")

    return {
        "node_id": node.id,
        "name": node.name,
        "status": status,
        "message": node.message,
        "address": node.address,
        "port": node.port,
        "realtime": realtime,
        "outbounds_sample": (outbounds or [])[:8],
        "issues": issues,
        "suggestions": suggestions,
        "healthy": status == NodeStatus.connected.value and not issues,
    }


async def build_panel_health(db: AsyncSession, *, admin: AdminDetails) -> dict[str, Any]:
    result: dict[str, Any] = {}

    try:
        enforce_permission(admin, "system", "read")
        resources = await SystemOperation.get_system_resource_stats()
        result["resources"] = resources.model_dump()
        users_stats = await SystemOperation.get_system_users_stats(db, admin=admin)
        result["users"] = users_stats.model_dump()
        workers = await get_workers_health()
        result["workers"] = workers.model_dump()
    except PermissionDenied:
        result["permission_denied"] = "system.read required for full panel health"

    recent_issues: list[dict[str, Any]] = []

    try:
        enforce_permission(admin, "nodes", "read")
        node_op = NodeOperation(operator_type=OperatorType.API)
        nodes_resp = await node_op.get_db_nodes(db, NodeListQuery(offset=0, limit=50))
        status_counts = Counter(
            (n.status.value if hasattr(n.status, "value") else str(n.status)) for n in nodes_resp.nodes
        )
        result["nodes"] = {
            "total": nodes_resp.total,
            "by_status": dict(status_counts),
            "items": [node_summary(n) for n in nodes_resp.nodes[:15]],
        }
        for node in nodes_resp.nodes:
            st = node.status.value if hasattr(node.status, "value") else str(node.status)
            if st in {NodeStatus.error.value, NodeStatus.connecting.value} and node.message:
                recent_issues.append(
                    {
                        "type": "node",
                        "id": node.id,
                        "name": node.name,
                        "status": st,
                        "message": node.message,
                    }
                )
    except PermissionDenied:
        result["nodes"] = {"permission_denied": True}

    result["recent_issues"] = recent_issues[:10]
    return result


async def diagnose_node_live(
    db: AsyncSession,
    *,
    admin: AdminDetails,
    node_id: int,
) -> dict[str, Any]:
    node_op = NodeOperation(operator_type=OperatorType.API)
    db_node = await node_op.get_validated_node(db, node_id)
    node = NodeResponse.model_validate(db_node)

    realtime_dict: dict[str, Any] | None = None
    outbounds_list: list[dict[str, Any]] | None = None
    stats_error: str | None = None

    try:
        enforce_permission(admin, "nodes", "stats")
        realtime = await node_op._get_node_stats_safe(node_id)
        if realtime is not None:
            realtime_dict = realtime.model_dump()
        try:
            latency_resp = await node_op.get_outbounds_latency(node_id)
            outbounds_list = [item.model_dump() for item in latency_resp.latencies]
        except Exception as exc:
            if not stats_error:
                stats_error = f"outbounds latency: {exc}"
    except PermissionDenied:
        stats_error = "nodes.stats permission required for live CPU/outbound probes"
    except Exception as exc:
        stats_error = str(exc)

    return diagnose_node_record(
        node,
        realtime=realtime_dict,
        outbounds=outbounds_list,
        stats_error=stats_error,
    )
