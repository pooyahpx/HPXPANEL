from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.manager import core_manager
from app.core.openvpn import OpenVPNConfig
from app.db.crud.wireguard import tags_from_groups
from app.db.models import CoreType
from app.models.proxy import OpenVPNSettings, ProxyTable
from app.utils.openvpn_pki import (
    cert_fingerprint_sha256,
    cert_serial_decimal,
    sign_client_certificate,
)
from app.utils.system import random_password


async def get_openvpn_core_for_inbounds(inbound_tags: set[str]) -> OpenVPNConfig | None:
    if not inbound_tags:
        return None
    cores = await core_manager.get_cores()
    for core in cores.values():
        if core.type != CoreType.openvpn:
            continue
        if set(core.inbounds) & inbound_tags:
            return core
    return None


async def user_has_openvpn_access(db: AsyncSession, groups: Iterable) -> bool:
    inbound_tags = await tags_from_groups(groups)
    return await get_openvpn_core_for_inbounds(inbound_tags) is not None


async def ensure_openvpn_credentials(
    db: AsyncSession,
    user_id: int,
    proxy_settings: ProxyTable,
    groups: Iterable,
    *,
    force: bool = False,
) -> ProxyTable:
    if not await user_has_openvpn_access(db, groups):
        return proxy_settings

    openvpn = proxy_settings.openvpn
    if not openvpn.username:
        openvpn.username = random_password()
    if not openvpn.password:
        openvpn.password = random_password()

    if openvpn.client_cert and openvpn.client_key and not force:
        # Keep serial in decimal form so it matches OpenVPN's tls_serial_0.
        openvpn.serial = cert_serial_decimal(openvpn.client_cert)
        if not openvpn.fingerprint:
            openvpn.fingerprint = cert_fingerprint_sha256(openvpn.client_cert)
        proxy_settings.openvpn = openvpn
        return proxy_settings

    inbound_tags = await tags_from_groups(groups)
    core = await get_openvpn_core_for_inbounds(inbound_tags)
    if core is None:
        proxy_settings.openvpn = openvpn
        return proxy_settings

    ca_key = str(core.get("ca_key") or "").strip()
    ca_cert = str(core.get("ca_cert") or "").strip()
    if not ca_key or not ca_cert:
        raise ValueError(
            "OpenVPN core is missing CA private key — open the core editor, regenerate PKI, and save the core again"
        )

    client_cert, client_key = sign_client_certificate(
        ca_key_pem=ca_key,
        ca_cert_pem=ca_cert,
        common_name=str(user_id),
    )
    openvpn.client_cert = client_cert
    openvpn.client_key = client_key
    openvpn.serial = cert_serial_decimal(client_cert)
    openvpn.fingerprint = cert_fingerprint_sha256(client_cert)
    proxy_settings.openvpn = openvpn
    return proxy_settings


def clear_openvpn_credentials(proxy_settings: ProxyTable) -> ProxyTable:
    proxy_settings.openvpn = OpenVPNSettings()
    return proxy_settings


def openvpn_settings_dict(settings: OpenVPNSettings | dict | None) -> dict:
    if settings is None:
        return {}
    if isinstance(settings, OpenVPNSettings):
        return settings.model_dump()
    return dict(settings)
