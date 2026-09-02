from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from app.core.manager import core_manager
from app.db import AsyncSession
from app.db.models import ProxyHost, ProxyHostFingerprint, ProxyHostSecurity
from app.models.admin import AdminDetails
from app.models.host import CreateHost, GRPCSettings, TransportSettings, WebSocketSettings
from app.models.proxy import ProxyTable, TrojanSettings, VlessSettings, VMessSettings
from app.models.user import UserCreate
from app.operation.host import HostOperation
from app.operation import OperatorType
from app.operation.user import UserOperation
from app.services.copilot.inbound_from_link import resolve_inbound_for_import
from app.services.copilot.proxy_uri import ParsedProxyLink, ProxyUriParseError, parse_proxy_link


def _map_security(security: str | None) -> ProxyHostSecurity:
    normalized = (security or "").strip().lower()
    if normalized in {"", "none"}:
        return ProxyHostSecurity.none
    if normalized in {"tls", "reality", "xtls"}:
        return ProxyHostSecurity.tls
    return ProxyHostSecurity.inbound_default


def _map_fingerprint(value: str | None) -> ProxyHostFingerprint:
    if not value:
        return ProxyHostFingerprint.none
    normalized = value.strip().lower()
    for item in ProxyHostFingerprint:
        if item.name == normalized or str(item.value).lower() == normalized:
            return item
    return ProxyHostFingerprint.none


def _build_transport_settings(parsed: ParsedProxyLink) -> TransportSettings | None:
    network = (parsed.network or "tcp").lower()
    if network == "ws":
        return TransportSettings(websocket_settings=WebSocketSettings())
    if network in {"grpc", "gun"}:
        return TransportSettings(grpc_settings=GRPCSettings())
    return None


def build_create_host_from_link(
    parsed: ParsedProxyLink,
    *,
    inbound_tag: str,
    priority: int,
    remark_override: str | None = None,
) -> CreateHost:
    remark = (remark_override or parsed.remark or f"{parsed.protocol}-{parsed.address}").strip()
    if not remark:
        remark = f"{parsed.protocol}-{parsed.address}"

    sni_set = {parsed.sni} if parsed.sni else set()
    host_set = set()
    if parsed.host_header:
        host_set.add(parsed.host_header)
    elif parsed.sni:
        host_set.add(parsed.sni)

    return CreateHost(
        remark=remark,
        address={parsed.address},
        inbound_tag=inbound_tag,
        port=parsed.port,
        sni=sni_set,
        host=host_set,
        path=parsed.path,
        security=_map_security(parsed.security),
        fingerprint=_map_fingerprint(parsed.fingerprint),
        allowinsecure=parsed.allow_insecure,
        transport_settings=_build_transport_settings(parsed),
        priority=priority,
    )


async def list_core_inbound_options() -> list[dict]:
    inbounds_by_tag = await core_manager.get_inbounds_by_tag()
    options: list[dict] = []
    for tag, settings in inbounds_by_tag.items():
        options.append(
            {
                "tag": tag,
                "protocol": settings.get("protocol"),
                "port": settings.get("port"),
                "network": settings.get("network"),
                "tls": settings.get("tls"),
            }
        )
    options.sort(key=lambda item: item["tag"] or "")
    return options


def suggest_inbound_tags(parsed: ParsedProxyLink, inbounds: list[dict]) -> list[str]:
    scored: list[tuple[int, str]] = []
    target_protocol = parsed.protocol
    target_network = (parsed.network or "tcp").lower()

    for inbound in inbounds:
        score = 0
        if inbound.get("protocol") == target_protocol:
            score += 3
        inbound_network = str(inbound.get("network") or "tcp").lower()
        if inbound_network == target_network:
            score += 2
        if inbound.get("port") == parsed.port:
            score += 1
        if score:
            scored.append((score, inbound["tag"]))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [tag for _, tag in scored[:5]]


async def next_host_priority(db: AsyncSession) -> int:
    current = (await db.execute(select(func.max(ProxyHost.priority)))).scalar_one_or_none()
    if current is None:
        return 0
    return int(current) + 1


def preview_host_import(
    parsed: ParsedProxyLink,
    *,
    inbound_tag: str,
    priority: int,
    remark_override: str | None = None,
) -> dict:
    host = build_create_host_from_link(
        parsed,
        inbound_tag=inbound_tag,
        priority=priority,
        remark_override=remark_override,
    )
    return {
        "parsed": parsed.to_public_dict(),
        "host": host.model_dump(mode="json"),
        "notes": [
            "Creates a Host in HPXPANEL. When create_inbound_if_missing=true, a matching Xray inbound is created in the core if needed.",
            "The link UUID/password is not applied unless create_user=true.",
        ],
    }


async def import_proxy_link(
    db: AsyncSession,
    *,
    admin: AdminDetails,
    link: str,
    inbound_tag: str = "",
    confirm: bool = False,
    remark_override: str | None = None,
    create_user: bool = False,
    username: str | None = None,
    group_ids: list[int] | None = None,
    core_id: int | None = None,
    create_inbound_if_missing: bool = True,
) -> dict:
    try:
        parsed = parse_proxy_link(link)
    except ProxyUriParseError as exc:
        return {"error": str(exc)}

    try:
        resolved_tag, inbound_meta = await resolve_inbound_for_import(
            db,
            admin=admin,
            parsed=parsed,
            inbound_tag=inbound_tag,
            core_id=core_id,
            create_inbound_if_missing=create_inbound_if_missing,
            confirm=confirm,
        )
    except ValueError as exc:
        inbounds = await list_core_inbound_options()
        return {
            "error": str(exc),
            "parsed": parsed.to_public_dict(),
            "suggested_inbound_tags": suggest_inbound_tags(parsed, inbounds),
            "available_inbounds": inbounds[:20],
        }

    priority = await next_host_priority(db)
    preview = preview_host_import(parsed, inbound_tag=resolved_tag, priority=priority, remark_override=remark_override)
    preview["inbound"] = inbound_meta

    if not confirm:
        inbounds = await list_core_inbound_options()
        preview["suggested_inbound_tags"] = suggest_inbound_tags(parsed, inbounds)
        preview["ready"] = True
        preview["message"] = "Preview only. Call again with confirm=true to create inbound (if needed) and host."
        return preview

    host_op = HostOperation(operator_type=OperatorType.API)
    created_host = await host_op.create_host(
        db,
        build_create_host_from_link(
            parsed,
            inbound_tag=resolved_tag,
            priority=priority,
            remark_override=remark_override,
        ),
        admin,
    )

    result = {
        "host_id": created_host.id,
        "host_remark": created_host.remark,
        "inbound_tag": resolved_tag,
        "parsed": parsed.to_public_dict(),
        "inbound": inbound_meta,
        "message": f"Host #{created_host.id} created",
    }

    if not create_user:
        return result

    if not username or not group_ids:
        result["user_error"] = "create_user requires username and group_ids"
        return result

    if parsed.protocol == "vless" and not parsed.client_id:
        result["user_error"] = "Link has no VLESS UUID — cannot create user"
        return result
    if parsed.protocol == "vmess" and not parsed.client_id:
        result["user_error"] = "Link has no VMess UUID — cannot create user"
        return result
    if parsed.protocol == "trojan" and not parsed.password:
        result["user_error"] = "Link has no Trojan password — cannot create user"
        return result

    proxy_settings = ProxyTable()
    if parsed.protocol == "vless":
        proxy_settings.vless = VlessSettings(id=UUID(parsed.client_id))
    elif parsed.protocol == "vmess":
        proxy_settings.vmess = VMessSettings(id=UUID(parsed.client_id))
    elif parsed.protocol == "trojan":
        proxy_settings.trojan = TrojanSettings(password=parsed.password or "")

    user_op = UserOperation(operator_type=OperatorType.API)
    created_user = await user_op.create_user(
        db,
        UserCreate(username=username, group_ids=group_ids, proxy_settings=proxy_settings),
        admin,
    )
    result["user_id"] = created_user.id
    result["username"] = created_user.username
    result["message"] += f"; user {created_user.username} created"
    return result
