from datetime import UTC, datetime

from app.models.observability import (
    NodeObservabilityCard,
    ObservabilitySummaryResponse,
    ProtocolHealth,
    ProtocolHealthStatus,
)
from app.observability.prometheus import render_metrics, update_from_summary


def test_prometheus_update_and_render():
    summary = ObservabilitySummaryResponse(
        generated_at=datetime.now(UTC),
        nodes=[
            NodeObservabilityCard(
                node_id=1,
                name="node-a",
                address="1.2.3.4",
                status="connected",
                cpu_usage=42.0,
                mem_usage_percent=55.0,
                incoming_mbps=1.5,
                outgoing_mbps=2.0,
                users_online=3,
                protocols=[ProtocolHealth(protocol="xray", status=ProtocolHealthStatus.healthy, latency_ms=80)],
            )
        ],
    )
    update_from_summary(summary)
    payload, content_type = render_metrics()
    assert content_type.startswith("text/plain")
    body = payload.decode("utf-8")
    assert "hpxpanel_node_cpu_usage_percent" in body
    assert 'node_id="1"' in body
