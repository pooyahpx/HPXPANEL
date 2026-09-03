from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.openvpn import OpenVPNConfig
from app.db.crud.core import get_core_config_by_id
from app.db.crud.node import get_node_by_id
from app.db.models import (
    CoreType,
    Group,
    ProxyInbound,
    User,
    UserStatus,
    inbounds_groups_association,
    users_groups_association,
)
from app.models.openvpn_ops import OpenVPNHealthCheck, OpenVPNNodeMonitoringResponse, OpenVPNUserMonitorEntry
from app.models.proxy import OpenVPNSettings, ProxyTable
from app.node import node_manager
from app.utils.openvpn_core import openvpn_ca_key_missing, openvpn_pki_ready
from PasarGuardNodeBridge import NodeAPIError


def _normalize_online_stats(stats) -> dict[str, int]:
    if stats is None:
        return {}
    name = (getattr(stats, "name", None) or "").strip().lower()
    value = int(getattr(stats, "value", 0) or 0)
    if name:
        return {name: value}
    if value:
        return {"connections": value}
    return {}


async def _fetch_user_ip_data(node_id: int, user_id: int) -> tuple[dict[str, int], dict[str, str], dict[str, int]]:
    node = await node_manager.get_node(node_id)
    if node is None:
        return {}, {}, {}

    email = str(user_id)
    ips: dict[str, int] = {}
    ip_protocol: dict[str, str] = {}
    protocols: dict[str, int] = {}

    try:
        stats = await node.get_user_online_ip_list(email=email)
        if stats is not None:
            ips = dict(stats.ips or {})
            if hasattr(stats, "ip_protocol"):
                ip_protocol = dict(stats.ip_protocol or {})
    except NodeAPIError:
        pass

    try:
        online = await node.get_user_online_stats(email=email)
        protocols = _normalize_online_stats(online)
        if not protocols and ips:
            protocols = {"openvpn": len(ips)}
    except NodeAPIError:
        if ips:
            protocols = {"openvpn": len(ips)}

    return ips, ip_protocol, protocols


async def _users_for_openvpn_core(db: AsyncSession, inbound_tags: set[str]) -> list[User]:
    if not inbound_tags:
        return []
    stmt = (
        select(User)
        .join(users_groups_association, users_groups_association.c.user_id == User.id)
        .join(Group, Group.id == users_groups_association.c.groups_id)
        .join(inbounds_groups_association, inbounds_groups_association.c.group_id == Group.id)
        .join(ProxyInbound, ProxyInbound.id == inbounds_groups_association.c.inbound_id)
        .where(ProxyInbound.tag.in_(inbound_tags))
        .where(User.status == UserStatus.active)
        .distinct()
    )
    return list((await db.execute(stmt)).scalars().all())


async def build_node_openvpn_monitoring(db: AsyncSession, node_id: int) -> OpenVPNNodeMonitoringResponse:
    db_node = await get_node_by_id(db, node_id)
    if db_node is None:
        raise ValueError("Node not found")

    core = await get_core_config_by_id(db, db_node.core_config_id)
    if core is None or core.type != CoreType.openvpn:
        return OpenVPNNodeMonitoringResponse(node_id=node_id, core_id=db_node.core_config_id)

    config = OpenVPNConfig(core.config, skip_validation=True)
    inbound_tags = set(config.inbounds)
    users = await _users_for_openvpn_core(db, inbound_tags)

    entries: list[OpenVPNUserMonitorEntry] = []
    for db_user in users:
        proxy = ProxyTable.model_validate(db_user.proxy_settings or {})
        openvpn: OpenVPNSettings = proxy.openvpn
        ips, ip_protocol, protocols = await _fetch_user_ip_data(node_id, db_user.id)
        openvpn_count = protocols.get("openvpn", 0)
        connection_count = openvpn_count or sum(protocols.values()) or len(ips)
        entries.append(
            OpenVPNUserMonitorEntry(
                user_id=db_user.id,
                username=db_user.username,
                has_certificate=bool(openvpn.client_cert and openvpn.client_key),
                serial=openvpn.serial or "",
                fingerprint=openvpn.fingerprint or "",
                online=connection_count > 0,
                connection_count=connection_count,
                ips=ips,
                ip_protocol=ip_protocol,
            )
        )

    entries.sort(key=lambda item: (not item.online, item.username.lower()))
    return OpenVPNNodeMonitoringResponse(
        node_id=node_id,
        core_id=core.id,
        core_name=core.name,
        pki_ready=openvpn_pki_ready(core.config),
        listener_port=int(config.get("port") or 0) or None,
        listener_proto=str(config.get("proto") or ""),
        users=entries,
    )


async def build_openvpn_health(
    db: AsyncSession,
    *,
    core_id: int,
    node_id: int | None = None,
    user_id: int | None = None,
) -> OpenVPNHealthCheck:
    issues: list[str] = []
    core = await get_core_config_by_id(db, core_id)
    if core is None:
        return OpenVPNHealthCheck(core_id=core_id, issues=["Core not found"])

    if core.type != CoreType.openvpn:
        return OpenVPNHealthCheck(core_id=core_id, issues=["Core is not OpenVPN"])

    pki_ready = openvpn_pki_ready(core.config)
    ca_missing = openvpn_ca_key_missing(core.config)
    if ca_missing:
        issues.append("CA certificate exists but CA private key (ca_key) is missing — regenerate PKI in core editor")
    elif not pki_ready:
        issues.append("OpenVPN PKI is incomplete — generate CA/server certificates in core editor")

    config = OpenVPNConfig(core.config, skip_validation=True)
    inbound_tags = set(config.inbounds)

    node_connected = False
    if node_id is not None:
        db_node = await get_node_by_id(db, node_id)
        if db_node is None:
            issues.append("Node not found")
        elif db_node.core_config_id != core_id:
            issues.append("Selected node is not using this OpenVPN core")
        else:
            from app.db.models import NodeStatus

            node_connected = db_node.status == NodeStatus.connected
            if not node_connected:
                issues.append("Node is not connected — check node status and sync")

    host_configured = False
    if inbound_tags:
        from app.db.crud.host import get_hosts
        from app.models.host import HostListQuery

        hosts = await get_hosts(db=db, query=HostListQuery(limit=500))
        host_configured = any(host.inbound_tag in inbound_tags for host in hosts)
        if not host_configured:
            issues.append("No host configured for this OpenVPN inbound tag")

    user_has_certificate = False
    user_in_group = False
    if user_id is not None:
        from app.db.crud.user import get_user_by_id

        db_user = await get_user_by_id(db, user_id)
        if db_user is None:
            issues.append("User not found")
        else:
            user_tags = set()
            for group in db_user.groups:
                for inbound in group.inbounds:
                    user_tags.add(inbound.tag)
            user_in_group = bool(user_tags & inbound_tags)
            if not user_in_group:
                issues.append("User is not assigned to a group with OpenVPN inbound access")

            proxy = ProxyTable.model_validate(db_user.proxy_settings or {})
            user_has_certificate = bool(proxy.openvpn.client_cert and proxy.openvpn.client_key)
            if user_in_group and not user_has_certificate:
                issues.append("User has OpenVPN access but no client certificate — renew cert or re-save user")

    ready = pki_ready and not ca_missing and node_connected and host_configured
    if user_id is not None:
        ready = ready and user_in_group and user_has_certificate

    return OpenVPNHealthCheck(
        core_id=core_id,
        node_id=node_id,
        user_id=user_id,
        pki_ready=pki_ready,
        ca_key_missing=ca_missing,
        node_connected=node_connected,
        user_has_certificate=user_has_certificate,
        user_in_openvpn_group=user_in_group,
        host_configured=host_configured,
        ready=ready,
        issues=issues,
    )
