from datetime import UTC, datetime

from app.db import AsyncSession
from app.db.crud.node import get_nodes
from app.models.admin import AdminDetails
from app.models.fleet import (
    FleetNodeSummary,
    FleetPulseSummary,
    FleetSummaryResponse,
    FleetTunnelSummary,
)
from app.models.hpx_tunnel import HpxTunnelsQuery
from app.models.node import NodeListQuery
from app.operation import BaseOperation, OperatorType
from app.operation.hpx_pulse import HpxPulseOperation
from app.operation.hpx_tunnel import HpxTunnelOperation


class FleetOperation(BaseOperation):
    def __init__(self, operator_type: OperatorType = OperatorType.API):
        super().__init__(operator_type)
        self._tunnels = HpxTunnelOperation(operator_type=operator_type)
        self._pulses = HpxPulseOperation(operator_type=operator_type)

    async def get_summary(self, db: AsyncSession, admin: AdminDetails) -> FleetSummaryResponse:
        # Use CRUD for nodes so last_status_change is available (NodeResponse omits it).
        db_nodes, _ = await get_nodes(db=db, query=NodeListQuery(offset=0, limit=500))
        tunnels_resp = await self._tunnels.list_tunnels(
            db, admin=admin, query=HpxTunnelsQuery(offset=0, limit=500)
        )
        pulses_resp = await self._pulses.list_pulses(db, admin=admin, offset=0, limit=500)

        nodes = [
            FleetNodeSummary(
                id=node.id,
                name=node.name,
                status=str(node.status.value if hasattr(node.status, "value") else node.status),
                address=node.address,
                node_version=node.node_version,
                xray_version=node.xray_version,
                last_status_change=node.last_status_change,
            )
            for node in db_nodes
        ]
        tunnels = [
            FleetTunnelSummary(
                id=tunnel.id,
                name=tunnel.name,
                status=str(tunnel.status.value if hasattr(tunnel.status, "value") else tunnel.status),
                agent_claimed=tunnel.agent_claimed,
                agent_last_seen=tunnel.agent_last_seen,
                agent_host=tunnel.agent_host,
            )
            for tunnel in tunnels_resp.tunnels
        ]
        pulses = [
            FleetPulseSummary(
                id=pulse.id,
                name=pulse.name,
                status=str(pulse.status.value if hasattr(pulse.status, "value") else pulse.status),
                iran_claimed=pulse.iran_claimed,
                abroad_claimed=pulse.abroad_claimed,
                iran_agent_last_seen=pulse.iran_agent_last_seen,
                abroad_agent_last_seen=pulse.abroad_agent_last_seen,
                iran_agent_host=pulse.iran_agent_host,
                abroad_agent_host=pulse.abroad_agent_host,
            )
            for pulse in pulses_resp.pulses
        ]

        return FleetSummaryResponse(
            generated_at=datetime.now(UTC),
            nodes=nodes,
            tunnels=tunnels,
            pulses=pulses,
            totals={
                "nodes": len(nodes),
                "tunnels": len(tunnels),
                "pulses": len(pulses),
            },
        )
