from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


class ProxyUriParseError(ValueError):
    pass


@dataclass(slots=True)
class ParsedProxyLink:
    protocol: str
    remark: str
    address: str
    port: int
    client_id: str | None = None
    password: str | None = None
    encryption: str | None = None
    security: str | None = None
    network: str | None = None
    sni: str | None = None
    host_header: str | None = None
    path: str | None = None
    flow: str | None = None
    fingerprint: str | None = None
    alpn: list[str] = field(default_factory=list)
    allow_insecure: bool | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "protocol": self.protocol,
            "remark": self.remark,
            "address": self.address,
            "port": self.port,
            "client_id": self.client_id,
            "password": self.password,
            "encryption": self.encryption,
            "security": self.security,
            "network": self.network,
            "sni": self.sni,
            "host_header": self.host_header,
            "path": self.path,
            "flow": self.flow,
            "fingerprint": self.fingerprint,
            "alpn": self.alpn,
            "allow_insecure": self.allow_insecure,
            "extra": self.extra,
        }


def _first(params: dict[str, list[str]], key: str) -> str | None:
    values = params.get(key)
    if not values:
        return None
    value = values[0]
    return value if value != "" else None


def _parse_boolish(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


def _split_host_port(hostport: str, default_port: int | None = None) -> tuple[str, int]:
    if hostport.startswith("["):
        match = re.match(r"^\[(.+)\]:(\d+)$", hostport)
        if not match:
            raise ProxyUriParseError("Invalid IPv6 host:port")
        return match.group(1), int(match.group(2))

    if ":" in hostport:
        host, port_raw = hostport.rsplit(":", 1)
        if not port_raw.isdigit():
            raise ProxyUriParseError(f"Invalid port in host: {hostport!r}")
        return host, int(port_raw)

    if default_port is None:
        raise ProxyUriParseError("Port is required")
    return hostport, default_port


def _parse_query_common(params: dict[str, list[str]], parsed: ParsedProxyLink) -> None:
    parsed.security = _first(params, "security") or parsed.security
    parsed.network = _first(params, "type") or _first(params, "net") or parsed.network
    parsed.sni = _first(params, "sni") or parsed.sni
    parsed.host_header = _first(params, "host") or parsed.host_header
    parsed.path = _first(params, "path") or parsed.path
    parsed.flow = _first(params, "flow") or parsed.flow
    parsed.fingerprint = _first(params, "fp") or parsed.fingerprint
    parsed.encryption = _first(params, "encryption") or parsed.encryption

    insecure = _parse_boolish(_first(params, "allowInsecure"))
    if insecure is None:
        insecure = _parse_boolish(_first(params, "insecure"))
    if insecure is not None:
        parsed.allow_insecure = insecure

    alpn = _first(params, "alpn")
    if alpn:
        parsed.alpn = [part.strip() for part in alpn.split(",") if part.strip()]


def parse_vless_uri(uri: str) -> ParsedProxyLink:
    parsed_url = urlparse(uri.strip())
    if parsed_url.scheme.lower() != "vless":
        raise ProxyUriParseError("Not a vless:// link")

    if not parsed_url.hostname or parsed_url.port is None:
        raise ProxyUriParseError("vless link must include host and port")

    params = parse_qs(parsed_url.query, keep_blank_values=True)
    result = ParsedProxyLink(
        protocol="vless",
        remark=unquote(parsed_url.fragment or ""),
        address=parsed_url.hostname,
        port=parsed_url.port,
        client_id=parsed_url.username or None,
    )
    _parse_query_common(params, result)
    return result


def parse_trojan_uri(uri: str) -> ParsedProxyLink:
    parsed_url = urlparse(uri.strip())
    if parsed_url.scheme.lower() != "trojan":
        raise ProxyUriParseError("Not a trojan:// link")

    if not parsed_url.hostname or parsed_url.port is None:
        raise ProxyUriParseError("trojan link must include host and port")

    params = parse_qs(parsed_url.query, keep_blank_values=True)
    result = ParsedProxyLink(
        protocol="trojan",
        remark=unquote(parsed_url.fragment or ""),
        address=parsed_url.hostname,
        port=parsed_url.port,
        password=unquote(parsed_url.username or ""),
    )
    _parse_query_common(params, result)
    return result


def parse_vmess_uri(uri: str) -> ParsedProxyLink:
    raw = uri.strip()
    if not raw.lower().startswith("vmess://"):
        raise ProxyUriParseError("Not a vmess:// link")

    payload = raw[8:]
    padding = "=" * (-len(payload) % 4)
    try:
        decoded = base64.b64decode(payload + padding).decode("utf-8")
        data = json.loads(decoded)
    except (ValueError, json.JSONDecodeError) as exc:
        raise ProxyUriParseError("Invalid vmess base64/json payload") from exc

    if not isinstance(data, dict):
        raise ProxyUriParseError("vmess payload must be a JSON object")

    address = str(data.get("add") or data.get("host") or "").strip()
    port_raw = data.get("port")
    if not address or port_raw in (None, ""):
        raise ProxyUriParseError("vmess payload missing address or port")

    result = ParsedProxyLink(
        protocol="vmess",
        remark=str(data.get("ps") or data.get("remark") or ""),
        address=address,
        port=int(port_raw),
        client_id=str(data.get("id") or "") or None,
        encryption=str(data.get("scy") or data.get("encryption") or "") or None,
        security=str(data.get("tls") or "") or None,
        network=str(data.get("net") or data.get("type") or "") or None,
        sni=str(data.get("sni") or "") or None,
        host_header=str(data.get("host") or "") or None,
        path=str(data.get("path") or "") or None,
    )
    if str(data.get("tls", "")).lower() in {"tls", "reality"}:
        result.security = str(data.get("tls")).lower()
    return result


def parse_shadowsocks_uri(uri: str) -> ParsedProxyLink:
    parsed_url = urlparse(uri.strip())
    if parsed_url.scheme.lower() not in {"ss", "shadowsocks"}:
        raise ProxyUriParseError("Not an ss:// link")

    remark = unquote(parsed_url.fragment or "")

    if parsed_url.hostname and parsed_url.port is not None:
        userinfo = unquote(parsed_url.username or "")
        if parsed_url.password:
            userinfo = f"{userinfo}:{unquote(parsed_url.password)}"
        if "@" in userinfo or ":" not in userinfo:
            padding = "=" * (-len(userinfo) % 4)
            try:
                userinfo = base64.urlsafe_b64decode(userinfo + padding).decode("utf-8")
            except ValueError as exc:
                raise ProxyUriParseError("Invalid shadowsocks credentials") from exc
        method, password = userinfo.split(":", 1)
        return ParsedProxyLink(
            protocol="shadowsocks",
            remark=remark,
            address=parsed_url.hostname,
            port=parsed_url.port,
            password=password,
            extra={"method": method},
        )

    token = (parsed_url.netloc or parsed_url.path.lstrip("/")).strip()
    padding = "=" * (-len(token) % 4)
    try:
        decoded = base64.urlsafe_b64decode(token + padding).decode("utf-8")
    except ValueError as exc:
        raise ProxyUriParseError("Invalid shadowsocks base64 payload") from exc

    if "@" in decoded:
        creds, hostport = decoded.rsplit("@", 1)
        method, password = creds.split(":", 1)
        address, port = _split_host_port(hostport)
    else:
        method, rest = decoded.split(":", 1)
        password, hostport = rest.rsplit("@", 1)
        address, port = _split_host_port(hostport)

    return ParsedProxyLink(
        protocol="shadowsocks",
        remark=remark,
        address=address,
        port=port,
        password=password,
        extra={"method": method},
    )


def parse_proxy_link(uri: str) -> ParsedProxyLink:
    raw = uri.strip()
    if not raw:
        raise ProxyUriParseError("Link is empty")

    lowered = raw.lower()
    if lowered.startswith("vless://"):
        return parse_vless_uri(raw)
    if lowered.startswith("vmess://"):
        return parse_vmess_uri(raw)
    if lowered.startswith("trojan://"):
        return parse_trojan_uri(raw)
    if lowered.startswith("ss://") or lowered.startswith("shadowsocks://"):
        return parse_shadowsocks_uri(raw)

    raise ProxyUriParseError("Unsupported link scheme — use vless://, vmess://, trojan://, or ss://")
