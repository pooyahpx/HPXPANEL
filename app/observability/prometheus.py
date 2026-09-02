"""Prometheus metrics for HPXPANEL observability."""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest

from app.observability.registry import get_registry


def _gauge(name: str, documentation: str, labelnames: tuple[str, ...] = ()) -> Gauge:
    return Gauge(name, documentation, labelnames, registry=get_registry())


NODE_CPU = _gauge("hpxpanel_node_cpu_usage_percent", "Node CPU usage percent", ("node_id", "node_name"))
NODE_MEM = _gauge("hpxpanel_node_memory_usage_percent", "Node memory usage percent", ("node_id", "node_name"))
NODE_NET_IN = _gauge(
    "hpxpanel_node_network_in_bytes_per_second",
    "Node incoming bandwidth bytes/s",
    ("node_id", "node_name"),
)
NODE_NET_OUT = _gauge(
    "hpxpanel_node_network_out_bytes_per_second",
    "Node outgoing bandwidth bytes/s",
    ("node_id", "node_name"),
)
NODE_ONLINE_USERS = _gauge("hpxpanel_node_online_users", "Approximate online users per node", ("node_id", "node_name"))
NODE_STATUS = _gauge("hpxpanel_node_up", "1 when node status is connected", ("node_id", "node_name"))
MASTER_CPU = _gauge("hpxpanel_master_cpu_usage_percent", "Panel host CPU usage percent")
MASTER_MEM = _gauge("hpxpanel_master_memory_usage_percent", "Panel host memory usage percent")
PROTOCOL_HEALTH = _gauge(
    "hpxpanel_protocol_health",
    "1 healthy, 0.5 degraded, 0 down",
    ("scope", "node_id", "protocol"),
)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(get_registry()), CONTENT_TYPE_LATEST


def _protocol_score(status: str) -> float:
    if status == "healthy":
        return 1.0
    if status == "degraded":
        return 0.5
    if status == "down":
        return 0.0
    return -1.0


def update_from_summary(summary) -> None:
    if summary.master is not None:
        resources = summary.master.resources
        if resources.cpu_usage is not None:
            MASTER_CPU.set(resources.cpu_usage)
        if resources.mem_total and resources.mem_used is not None:
            MASTER_MEM.set((resources.mem_used / resources.mem_total) * 100)

    for card in summary.nodes:
        labels = (str(card.node_id), card.name)
        NODE_STATUS.labels(*labels).set(1 if card.status == "connected" else 0)
        if card.cpu_usage is not None:
            NODE_CPU.labels(*labels).set(card.cpu_usage)
        if card.mem_usage_percent is not None:
            NODE_MEM.labels(*labels).set(card.mem_usage_percent)
        if card.incoming_mbps is not None:
            NODE_NET_IN.labels(*labels).set(card.incoming_mbps * 1_000_000)
        if card.outgoing_mbps is not None:
            NODE_NET_OUT.labels(*labels).set(card.outgoing_mbps * 1_000_000)
        NODE_ONLINE_USERS.labels(*labels).set(card.users_online)
        for protocol in card.protocols:
            score = _protocol_score(protocol.status.value)
            if score >= 0:
                PROTOCOL_HEALTH.labels("node", str(card.node_id), protocol.protocol).set(score)
