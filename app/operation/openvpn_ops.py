from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.openvpn import OpenVPNConfig
from app.db.crud.core import get_core_config_by_id
from app.db.crud.group import create_group
from app.db.crud.node import get_node_by_id
from app.db.models import CoreType
from app.models.admin import AdminDetails
from app.models.group import GroupCreate
from app.models.host import CreateHost
from app.models.openvpn_ops import OpenVPNHealthCheck, OpenVPNNodeMonitoringResponse, OpenVPNOnboardingRequest, OpenVPNOnboardingResponse
from app.models.user import UserCreate
from app.operation import BaseOperation
from app.operation.host import HostOperation
from app.operation.user import UserOperation
from app.services.openvpn.monitoring import build_node_openvpn_monitoring, build_openvpn_health
from app.utils.openvpn_core import openvpn_pki_ready


def _slug_username(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip().lower()).strip("_")
    return cleaned[:32] or "openvpn_test"


class OpenVPNOperation(BaseOperation):
    async def get_node_monitoring(self, db: AsyncSession, node_id: int) -> OpenVPNNodeMonitoringResponse:
        try:
            return await build_node_openvpn_monitoring(db, node_id)
        except ValueError as exc:
            await self.raise_error(message=str(exc), code=404)

    async def get_health(
        self,
        db: AsyncSession,
        *,
        core_id: int,
        node_id: int | None = None,
        user_id: int | None = None,
    ) -> OpenVPNHealthCheck:
        return await build_openvpn_health(db, core_id=core_id, node_id=node_id, user_id=user_id)

    async def run_onboarding(
        self,
        db: AsyncSession,
        payload: OpenVPNOnboardingRequest,
        admin: AdminDetails,
    ) -> OpenVPNOnboardingResponse:
        core = await get_core_config_by_id(db, payload.core_id)
        if core is None:
            await self.raise_error(message="Core not found", code=404)
        if core.type != CoreType.openvpn:
            await self.raise_error(message="Core must be OpenVPN type", code=400)
        if not openvpn_pki_ready(core.config):
            await self.raise_error(
                message="OpenVPN PKI is incomplete — open core editor, generate PKI, and save before onboarding",
                code=400,
            )

        db_node = await get_node_by_id(db, payload.node_id)
        if db_node is None:
            await self.raise_error(message="Node not found", code=404)
        if db_node.core_config_id != payload.core_id:
            await self.raise_error(message="Node must use the selected OpenVPN core", code=400)

        ovpn = OpenVPNConfig(core.config, skip_validation=True)
        inbound_tag = ovpn.inbounds[0] if ovpn.inbounds else str(core.config.get("inbound_tag") or "openvpn")
        host_port = payload.host_port or int(core.config.get("port") or 1194)

        group = await create_group(
            db,
            GroupCreate(name=payload.group_name.strip(), inbound_tags=[inbound_tag]),
        )

        host_op = HostOperation(operator_type=self.operator_type)
        host = await host_op.create_host(
            db,
            CreateHost(
                remark="OpenVPN {USERNAME}",
                address=[payload.host_address.strip()],
                port=host_port,
                inbound_tag=inbound_tag,
                priority=1,
            ),
            admin,
        )

        user_op = UserOperation(operator_type=self.operator_type)
        username = _slug_username(payload.test_username)
        user = await user_op.create_user(
            db,
            UserCreate(username=username, group_ids=[group.id]),
            admin,
        )

        health = await build_openvpn_health(
            db,
            core_id=payload.core_id,
            node_id=payload.node_id,
            user_id=user.id,
        )

        return OpenVPNOnboardingResponse(
            core_id=payload.core_id,
            node_id=payload.node_id,
            group_id=group.id,
            host_id=host.id,
            user_id=user.id,
            username=user.username,
            subscription_url=user.subscription_url or "",
            health=health,
        )
