from __future__ import annotations

import copy
import re
from typing import Any

from app.db import AsyncSession
from app.db.crud.core import get_core_config_by_id, get_core_configs
from app.db.models import CoreType
from app.models.admin import AdminDetails
from app.models.core import CoreCreate, CoreListQuery
from app.operation import OperatorType
from app.operation.core import CoreOperation
from app.services.copilot.proxy_uri import ParsedProxyLink

_UNSUPPORTED_AUTO_SECURITY = frozenset({"reality", "xtls"})


def _normalize_network(value: str | None) -> str:
    network = (value or "tcp").strip().lower()
    if network in {"gun"}:
        return "grpc"
    return network


def _normalize_security(value: str | None) -> str:
    security = (value or "none").strip().lower()
    if security in {"", "none"}:
        return "none"
    return security


def _sanitize_tag_part(value: str) -> str:
    cleaned = re.sub(r"[^\w\s\-+]", "", value, flags=re.UNICODE).strip()
    return cleaned[:48] or "import"


def default_inbound_tag(parsed: ParsedProxyLink) -> str:
    remark = _sanitize_tag_part(parsed.remark or "")
    if remark:
        return remark
    network = _normalize_network(parsed.network).upper()
    return f"{parsed.protocol.upper()} {network} {parsed.port}"


def unique_inbound_tag(existing: set[str], base: str) -> str:
    if base not in existing:
        return base
    for index in range(2, 100):
        candidate = f"{base} ({index})"
        if candidate not in existing:
            return candidate
    raise ValueError("Could not allocate a unique inbound tag")


def inbound_matches_link(inbound: dict[str, Any], parsed: ParsedProxyLink) -> bool:
    if inbound.get("protocol") != parsed.protocol:
        return False
    if inbound.get("port") != parsed.port:
        return False
    stream = inbound.get("streamSettings") or {}
    if _normalize_network(stream.get("network")) != _normalize_network(parsed.network):
        return False
    return _normalize_security(stream.get("security")) == _normalize_security(parsed.security)


def _apply_stream_settings(inbound: dict[str, Any], parsed: ParsedProxyLink) -> None:
    network = _normalize_network(parsed.network)
    security = _normalize_security(parsed.security)
    stream: dict[str, Any] = {"network": network, "security": security}
    path = (parsed.path or "/").strip() or "/"
    host = (parsed.host_header or parsed.sni or "").strip()

    if network == "ws":
        stream["wsSettings"] = {"path": path, "host": host}
    elif network == "grpc":
        stream["grpcSettings"] = {"serviceName": path.lstrip("/"), "authority": host}
    elif network == "httpupgrade":
        stream["httpupgradeSettings"] = {"path": path, "host": host}
    elif network == "xhttp":
        stream["xhttpSettings"] = {"path": path, "host": host}
    elif network in {"tcp", "raw"}:
        stream["network"] = network
        if path not in {"", "/"} or host:
            stream[f"{network}Settings"] = {
                "header": {
                    "type": "http",
                    "request": {
                        "path": [path],
                        "headers": {"Host": [host]} if host else {},
                    },
                }
            }
    elif network == "h2":
        stream["httpSettings"] = {"path": path, "host": [host] if host else []}

    if security == "tls":
        stream["tlsSettings"] = {
            "serverName": parsed.sni or host or "",
            "alpn": parsed.alpn or ["h2", "http/1.1"],
        }
        if parsed.fingerprint:
            stream["tlsSettings"]["fingerprint"] = parsed.fingerprint

    inbound["streamSettings"] = stream


def build_xray_inbound_from_link(parsed: ParsedProxyLink, *, tag: str) -> dict[str, Any]:
    security = _normalize_security(parsed.security)
    if security in _UNSUPPORTED_AUTO_SECURITY:
        raise ValueError(
            f"Cannot auto-create inbound with security={security}. "
            "Create the inbound manually in Core Editor (REALITY/XTLS need keys)."
        )

    inbound: dict[str, Any] = {
        "tag": tag,
        "listen": "0.0.0.0",
        "port": parsed.port,
        "protocol": parsed.protocol,
        "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"]},
    }

    if parsed.protocol == "vless":
        inbound["settings"] = {"clients": [], "decryption": "none"}
        if parsed.flow:
            inbound["settings"]["flow"] = parsed.flow
    elif parsed.protocol == "vmess" or parsed.protocol == "trojan":
        inbound["settings"] = {"clients": []}
    elif parsed.protocol == "shadowsocks":
        method = str(parsed.extra.get("method") or "aes-256-gcm")
        inbound["settings"] = {"clients": [], "method": method}
    else:
        raise ValueError(f"Auto inbound creation is not supported for protocol {parsed.protocol}")

    _apply_stream_settings(inbound, parsed)
    return inbound


def _core_has_inbound_tag(core: Any, tag: str) -> bool:
    config = core.config or {}
    for inbound in config.get("inbounds") or []:
        if isinstance(inbound, dict) and str(inbound.get("tag") or "") == tag:
            return True
    return False


async def pick_xray_core(db: AsyncSession, core_id: int | None, *, inbound_tag: str = "") -> Any:
    cores, _ = await get_core_configs(db, CoreListQuery(limit=100))
    xray_cores = [core for core in cores if core.type in (CoreType.xray, None)]
    if not xray_cores:
        raise ValueError("No Xray core found — create an Xray core first")

    if core_id is not None:
        core = await get_core_config_by_id(db, core_id)
        if core is None:
            raise ValueError(f"Core #{core_id} not found")
        if core.type not in (CoreType.xray, None):
            raise ValueError(f"Core #{core_id} is not an Xray core")
        return core

    requested = inbound_tag.strip()
    if requested:
        for core in xray_cores:
            if _core_has_inbound_tag(core, requested):
                return core

    return xray_cores[0]


def _find_matching_inbound(config: dict, parsed: ParsedProxyLink) -> str | None:
    for inbound in config.get("inbounds") or []:
        if isinstance(inbound, dict) and inbound_matches_link(inbound, parsed):
            tag = inbound.get("tag")
            if tag:
                return str(tag)
    return None


async def add_inbound_to_core(
    db: AsyncSession,
    *,
    admin: AdminDetails,
    core_id: int,
    inbound: dict[str, Any],
) -> str:
    core_op = CoreOperation(operator_type=OperatorType.API)
    db_core = await core_op.get_validated_core_config(db, core_id)
    config = copy.deepcopy(db_core.config or {})
    inbounds = list(config.get("inbounds") or [])
    existing_tags = {str(item.get("tag")) for item in inbounds if item.get("tag")}
    tag = str(inbound.get("tag") or "")
    if not tag:
        raise ValueError("Inbound tag is required")
    if tag in existing_tags:
        raise ValueError(f"Inbound tag {tag!r} already exists in core {db_core.name!r}")

    inbounds.append(inbound)
    config["inbounds"] = inbounds

    modified = CoreCreate(
        name=db_core.name,
        config=config,
        type=db_core.type,
        exclude_inbound_tags=set(db_core.exclude_inbound_tags or []),
        fallbacks_inbound_tags=set(db_core.fallbacks_inbound_tags or []),
    )
    await core_op.modify_core(db, core_id, modified, admin)
    return tag


async def resolve_inbound_for_import(
    db: AsyncSession,
    *,
    admin: AdminDetails,
    parsed: ParsedProxyLink,
    inbound_tag: str = "",
    core_id: int | None = None,
    create_inbound_if_missing: bool = True,
    confirm: bool = False,
) -> tuple[str, dict[str, Any]]:
    """Resolve an inbound tag — reuse a match or create one from the share link."""
    core = await pick_xray_core(db, core_id, inbound_tag=inbound_tag)
    config = core.config or {}
    inbounds = [item for item in (config.get("inbounds") or []) if isinstance(item, dict)]
    existing_tags = {str(item.get("tag")) for item in inbounds if item.get("tag")}

    requested = inbound_tag.strip()
    if requested:
        if requested not in existing_tags:
            raise ValueError(f"Inbound tag {requested!r} was not found in core {core.name!r}")
        return requested, {"core_id": core.id, "core_name": core.name, "inbound_created": False}

    matched = _find_matching_inbound(config, parsed)
    if matched:
        return matched, {"core_id": core.id, "core_name": core.name, "inbound_created": False, "matched": True}

    if not create_inbound_if_missing:
        raise ValueError("No matching inbound for this link. Pass inbound_tag or enable create_inbound_if_missing.")

    proposed_tag = unique_inbound_tag(existing_tags, default_inbound_tag(parsed))
    proposed_inbound = build_xray_inbound_from_link(parsed, tag=proposed_tag)
    meta = {
        "core_id": core.id,
        "core_name": core.name,
        "inbound_created": False,
        "proposed_inbound_tag": proposed_tag,
        "proposed_inbound": proposed_inbound,
    }

    if not confirm:
        meta["message"] = "Will create this inbound on confirm=true"
        return proposed_tag, meta

    created_tag = await add_inbound_to_core(db, admin=admin, core_id=core.id, inbound=proposed_inbound)
    meta["inbound_created"] = True
    meta["message"] = f"Created inbound {created_tag!r} in core {core.name!r}"
    return created_tag, meta
