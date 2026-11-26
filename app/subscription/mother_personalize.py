"""Rewrite mother share-link credentials to the local user's proxies.

When the mother server is a Node of this panel (or has the same user clients),
traffic and online status are recorded against the local user — fixing unlimited
shared-UUID freeloading.
"""

from __future__ import annotations

import base64
import json
from typing import Any
from urllib.parse import quote, urlparse, urlunparse

from app.services.copilot.proxy_uri import ProxyUriParseError, parse_proxy_link


def _proxy_table(user) -> Any | None:
    ps = getattr(user, "proxy_settings", None)
    if ps is None:
        return None
    if hasattr(ps, "vless"):
        return ps
    if isinstance(ps, dict):
        return ps
    if hasattr(ps, "dict"):
        try:
            return ps.dict()
        except Exception:
            return None
    return None


def _get_attr(obj: Any, *keys: str, default=None):
    cur = obj
    for key in keys:
        if cur is None:
            return default
        if isinstance(cur, dict):
            cur = cur.get(key, default)
        else:
            cur = getattr(cur, key, default)
    return cur if cur is not None else default


def local_credential_for_protocol(user, protocol: str) -> str | None:
    """Return UUID/password for the given share-link protocol from local proxy_settings."""
    table = _proxy_table(user)
    if table is None:
        return None
    proto = (protocol or "").lower()
    if proto == "vless":
        value = _get_attr(table, "vless", "id")
        return str(value) if value else None
    if proto == "vmess":
        value = _get_attr(table, "vmess", "id")
        return str(value) if value else None
    if proto == "trojan":
        value = _get_attr(table, "trojan", "password")
        return str(value) if value else None
    if proto in {"shadowsocks", "ss"}:
        value = _get_attr(table, "shadowsocks", "password")
        return str(value) if value else None
    return None


def personalize_share_link(link: str, user, *, name: str | None = None) -> str:
    """Swap mother UUID/password with the local user's credential; keep host/params."""
    cleaned = (link or "").strip()
    if not cleaned or user is None:
        return cleaned

    try:
        parsed = parse_proxy_link(cleaned)
    except ProxyUriParseError:
        return cleaned

    local = local_credential_for_protocol(user, parsed.protocol)
    if not local:
        return cleaned

    remark = (name or "").strip() or parsed.remark or ""

    if parsed.protocol == "vless":
        base = cleaned.rsplit("#", 1)[0]
        parts = urlparse(base)
        # username holds UUID
        netloc = f"{local}@{parts.hostname}"
        if parts.port:
            netloc = f"{local}@{parts.hostname}:{parts.port}"
        rebuilt = urlunparse((parts.scheme, netloc, parts.path, parts.params, parts.query, ""))
        return f"{rebuilt}#{quote(remark)}" if remark else rebuilt

    if parsed.protocol == "trojan":
        base = cleaned.rsplit("#", 1)[0]
        parts = urlparse(base)
        netloc = f"{quote(local, safe='')}@{parts.hostname}"
        if parts.port:
            netloc = f"{quote(local, safe='')}@{parts.hostname}:{parts.port}"
        rebuilt = urlunparse((parts.scheme, netloc, parts.path, parts.params, parts.query, ""))
        return f"{rebuilt}#{quote(remark)}" if remark else rebuilt

    if parsed.protocol == "vmess":
        raw = cleaned.strip()
        payload = raw[8:]
        padding = "=" * (-len(payload) % 4)
        try:
            data = json.loads(base64.b64decode(payload + padding).decode("utf-8"))
        except Exception:
            return cleaned
        if not isinstance(data, dict):
            return cleaned
        data["id"] = local
        if remark:
            data["ps"] = remark
        encoded = base64.b64encode(json.dumps(data, separators=(",", ":")).encode("utf-8")).decode("utf-8")
        return f"vmess://{encoded}"

    if parsed.protocol == "shadowsocks":
        # Prefer SIP002: ss://base64(method:password)@host:port#remark
        method = str((parsed.extra or {}).get("method") or "chacha20-ietf-poly1305")
        userinfo = base64.urlsafe_b64encode(f"{method}:{local}".encode()).decode().rstrip("=")
        rebuilt = f"ss://{userinfo}@{parsed.address}:{parsed.port}"
        return f"{rebuilt}#{quote(remark)}" if remark else rebuilt

    return cleaned
