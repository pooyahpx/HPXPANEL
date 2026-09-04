from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.fleet import (
    FleetNodeSummary,
    FleetPulseSummary,
    FleetSummaryResponse,
    FleetTunnelSummary,
)
from app.operation.fleet import FleetOperation


@pytest.mark.asyncio
async def test_fleet_summary_shape(monkeypatch: pytest.MonkeyPatch):
    op = FleetOperation()

    node = MagicMock()
    node.id = 1
    node.name = "edge-1"
    node.status = MagicMock(value="connected")
    node.address = "1.2.3.4"
    node.node_version = "v1.2.3"
    node.xray_version = "1.8.0"
    node.last_status_change = datetime(2026, 1, 2, tzinfo=UTC)

    tunnel = MagicMock()
    tunnel.id = 10
    tunnel.name = "icmp-a"
    tunnel.status = MagicMock(value="running")
    tunnel.agent_claimed = True
    tunnel.agent_last_seen = datetime(2026, 1, 3, tzinfo=UTC)
    tunnel.agent_host = "iran-host"

    pulse = MagicMock()
    pulse.id = 20
    pulse.name = "pulse-a"
    pulse.status = MagicMock(value="running")
    pulse.iran_claimed = True
    pulse.abroad_claimed = False
    pulse.iran_agent_last_seen = datetime(2026, 1, 4, tzinfo=UTC)
    pulse.abroad_agent_last_seen = None
    pulse.iran_agent_host = "tehran"
    pulse.abroad_agent_host = None

    async def fake_get_nodes(db, query):
        return [node], 1

    monkeypatch.setattr("app.operation.fleet.get_nodes", fake_get_nodes)
    op._tunnels.list_tunnels = AsyncMock(return_value=MagicMock(tunnels=[tunnel], total=1))
    op._pulses.list_pulses = AsyncMock(return_value=MagicMock(pulses=[pulse], total=1))

    summary = await op.get_summary(db=MagicMock(), admin=MagicMock())

    assert isinstance(summary, FleetSummaryResponse)
    assert summary.totals == {"nodes": 1, "tunnels": 1, "pulses": 1}
    assert isinstance(summary.nodes[0], FleetNodeSummary)
    assert summary.nodes[0].model_dump() == {
        "id": 1,
        "name": "edge-1",
        "status": "connected",
        "address": "1.2.3.4",
        "node_version": "v1.2.3",
        "xray_version": "1.8.0",
        "last_status_change": datetime(2026, 1, 2, tzinfo=UTC),
    }
    assert isinstance(summary.tunnels[0], FleetTunnelSummary)
    assert summary.tunnels[0].agent_claimed is True
    assert summary.tunnels[0].agent_host == "iran-host"
    assert isinstance(summary.pulses[0], FleetPulseSummary)
    assert summary.pulses[0].iran_claimed is True
    assert summary.pulses[0].abroad_claimed is False
    assert summary.pulses[0].iran_agent_host == "tehran"
    assert summary.generated_at.tzinfo is not None
