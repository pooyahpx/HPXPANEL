from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.manager import core_manager
from app.db import AsyncSession
from app.db.crud.node import get_nodes
from app.db.crud.observability import count_total_users, get_online_users_by_node, get_recent_alert_events
from app.db.models import HpxPulse, HpxPulseStatus, Node, NodeStatus
from app.models.node import NodeListQuery
from app.models.observability import (
    MasterObservabilityCard,
    NodeObservabilityCard,
    ObservabilitySummaryResponse,
    ProtocolHealth,
    ProtocolHealthStatus,
)
from app.models.stats import Period
from app.models.system import WorkerHealth, WorkersHealth
from app.nats import is_nats_enabled
from app.nats.node_rpc import node_nats_client
from app.nats.scheduler_rpc import scheduler_nats_client
from app.operation import BaseOperation, OperatorType
from app.operation.node import NodeOperation
from app.operation.system import SystemOperation
from config import database_settings, observability_settings, usage_settings

_PROTOCOL_LABELS = {
    "xray": "xray",
    "wg": "wireguard",
    "openvpn": "openvpn",
    "ikev2": "ikev2",
    "l2tp": "l2tp",
    "mtproto": "mtproto",
    "singbox": "sing-box",
}


def _bps_to_mbps(value: int | None) -> float | None:
    if value is None:
        return None
    return round(value / 1_000_000, 2)


def _mem_percent(used: int | None, total: int | None) -> float | None:
    if not total or used is None:
        return None
    return round((used / total) * 100, 1)


def _latency_status(delay_ms: int | None, *, alive: bool | None = None) -> ProtocolHealthStatus:
    if alive is False:
        return ProtocolHealthStatus.down
    if delay_ms is None:
        return ProtocolHealthStatus.unknown
    if delay_ms <= 0:
        return ProtocolHealthStatus.down
    if delay_ms < 250:
        return ProtocolHealthStatus.healthy
    if delay_ms < 800:
        return ProtocolHealthStatus.degraded
    return ProtocolHealthStatus.down


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


class ObservabilityOperation(BaseOperation):
    def __init__(self) -> None:
        super().__init__(OperatorType.API)
        self._node_operation = NodeOperation(operator_type=OperatorType.API)
        self._system_operation = SystemOperation()

    async def get_summary(self, db: AsyncSession, admin) -> ObservabilitySummaryResponse:
        nodes, _ = await get_nodes(db, NodeListQuery(limit=500))
        online_by_node = await get_online_users_by_node(db)
        users_total = await count_total_users(db)

        realtime_stats = {}
        if nodes:
            try:
                realtime_stats = await self._node_operation.get_nodes_system_stats()
            except Exception:
                realtime_stats = {}

        latency_by_node: dict[int, dict[str, int]] = {}
        if observability_settings.probe_outbound_latency:
            connected_ids = [node.id for node in nodes if node.status == NodeStatus.connected]
            latency_results = await asyncio.gather(
                *[
                    self._safe_outbound_latency(node_id)
                    for node_id in connected_ids[: observability_settings.max_latency_probes]
                ],
                return_exceptions=True,
            )
            for node_id, result in zip(connected_ids, latency_results, strict=True):
                if isinstance(result, dict):
                    latency_by_node[node_id] = result

        core_protocols_by_id = await self._core_protocols_by_id()
        pulse_health = await self._pulse_protocol_health(db)

        node_cards: list[NodeObservabilityCard] = []
        for node in nodes:
            stats = realtime_stats.get(node.id)
            latency_map = latency_by_node.get(node.id, {})
            protocols = self._build_node_protocols(node, core_protocols_by_id, latency_map)
            if node.status != NodeStatus.connected:
                protocols = [
                    ProtocolHealth(protocol=item.protocol, status=ProtocolHealthStatus.down, detail=node.status.value)
                    for item in protocols
                ] or [ProtocolHealth(protocol="node", status=ProtocolHealthStatus.down, detail=node.status.value)]

            node_cards.append(
                NodeObservabilityCard(
                    node_id=node.id,
                    name=node.name,
                    address=node.address,
                    status=node.status.value,
                    cpu_usage=round(stats.cpu_usage, 1) if stats else None,
                    mem_usage_percent=_mem_percent(stats.mem_used, stats.mem_total) if stats else None,
                    incoming_mbps=_bps_to_mbps(stats.incoming_bandwidth_speed if stats else None),
                    outgoing_mbps=_bps_to_mbps(stats.outgoing_bandwidth_speed if stats else None),
                    uptime_seconds=stats.uptime if stats else None,
                    users_total=users_total,
                    users_online=online_by_node.get(node.id, 0),
                    protocols=protocols,
                    latency_ms=self._average_latency(latency_map) or pulse_health.get("latency_ms"),
                    packet_loss_percent=pulse_health.get("packet_loss_percent"),
                )
            )

        master_card = None
        try:
            resources = await self._system_operation.get_system_resource_stats()
            users = await self._system_operation.get_system_users_stats(db, admin)
            master_card = MasterObservabilityCard(
                resources=resources,
                users=users,
                protocols=[
                    ProtocolHealth(protocol="panel", status=ProtocolHealthStatus.healthy),
                    *pulse_health.get("protocols", []),
                ],
            )
        except Exception:
            master_card = None

        workers = await self._get_workers_health()
        recent_alerts = await get_recent_alert_events(db, limit=20)
        summary = ObservabilitySummaryResponse(
            generated_at=datetime.now(UTC),
            master=master_card,
            nodes=node_cards,
            workers=workers,
            recent_alerts=recent_alerts,
            node_stats_recording_enabled=bool(
                database_settings.is_postgresql and usage_settings.enable_recording_nodes_stats
            ),
        )

        if observability_settings.prometheus_enabled:
            from app.observability.prometheus import update_from_summary

            update_from_summary(summary)

        return summary

    async def get_history(
        self,
        db: AsyncSession,
        *,
        node_id: int | None,
        hours: int = 24,
    ):
        from app.db.crud.observability import get_system_stats_history

        end = datetime.now(UTC)
        start = end - timedelta(hours=max(1, min(hours, 24 * 30)))
        period = Period.hour if hours > 6 else Period.minute
        stats = await get_system_stats_history(db, node_id=node_id, start=start, end=end, period=period)
        return {
            "scope": "node" if node_id is not None else "master",
            "node_id": node_id,
            "stats": stats,
        }

    async def _safe_outbound_latency(self, node_id: int) -> dict[str, int]:
        try:
            response = await self._node_operation.get_outbounds_latency(
                node_id,
                timeout=observability_settings.latency_probe_timeout_seconds,
            )
        except Exception:
            return {}
        latency_map: dict[str, int] = {}
        for item in response.latencies:
            if item.alive and item.delay > 0:
                latency_map[item.name] = item.delay
        return latency_map

    async def _core_protocols_by_id(self) -> dict[int, set[str]]:
        mapping: dict[int, set[str]] = {}
        cores = await core_manager.get_cores()
        for core_id, core in cores.items():
            label = _PROTOCOL_LABELS.get(core.type)
            if label is None:
                continue
            mapping.setdefault(core_id, set()).add(label)
        return mapping

    def _build_node_protocols(
        self,
        node: Node,
        core_protocols_by_id: dict[int, set[str]],
        latency_map: dict[str, int],
    ) -> list[ProtocolHealth]:
        labels = sorted(core_protocols_by_id.get(node.core_config_id or -1, set()))
        if not labels:
            labels = ["xray"]
        protocols: list[ProtocolHealth] = []
        for label in labels:
            delay = latency_map.get(label) or (min(latency_map.values()) if latency_map else None)
            protocols.append(
                ProtocolHealth(
                    protocol=label,
                    status=_latency_status(delay, alive=node.status == NodeStatus.connected),
                    latency_ms=delay,
                )
            )
        return protocols

    @staticmethod
    def _average_latency(latency_map: dict[str, int]) -> float | None:
        if not latency_map:
            return None
        return round(sum(latency_map.values()) / len(latency_map), 1)

    async def _get_workers_health(self) -> WorkersHealth | None:
        if not is_nats_enabled():
            disabled = WorkerHealth(status="disabled")
            return WorkersHealth(scheduler=disabled, node=disabled)
        timeout = 5.0
        scheduler_task = _measure_worker_health(scheduler_nats_client.request("health_check", {}, timeout))
        node_task = _measure_worker_health(node_nats_client.request("health_check", {}, timeout))
        scheduler_health, node_health = await asyncio.gather(scheduler_task, node_task)
        return WorkersHealth(scheduler=scheduler_health, node=node_health)

    async def _pulse_protocol_health(self, db: AsyncSession) -> dict:
        stmt = (
            select(HpxPulse)
            .where(
                HpxPulse.enabled.is_(True),
                HpxPulse.status.in_(
                    [
                        HpxPulseStatus.running,
                        HpxPulseStatus.partial,
                        HpxPulseStatus.unhealthy,
                        HpxPulseStatus.error,
                    ]
                ),
            )
            .order_by(HpxPulse.created_at.desc())
            .limit(1)
        )
        row = (await db.execute(stmt)).scalar_one_or_none()
        if row is None:
            return {"protocols": [], "latency_ms": None, "packet_loss_percent": None}
        status = ProtocolHealthStatus.healthy
        if row.status in {HpxPulseStatus.unhealthy, HpxPulseStatus.error}:
            status = ProtocolHealthStatus.down
        elif row.status == HpxPulseStatus.partial:
            status = ProtocolHealthStatus.degraded
        return {
            "protocols": [
                ProtocolHealth(
                    protocol="pulse",
                    status=status,
                    latency_ms=int(row.latency_ms) if row.latency_ms else None,
                    detail=row.status.value,
                )
            ],
            "latency_ms": float(row.latency_ms) if row.latency_ms is not None else None,
            "packet_loss_percent": float(row.packet_loss_pct) if row.packet_loss_pct is not None else None,
        }
