from __future__ import annotations

import base64
import json

import pytest

from app.db.crud.admin import get_admin
from app.services.copilot.host_import import (
    import_proxy_link,
    preview_host_import,
    suggest_inbound_tags,
)
from app.services.copilot.proxy_uri import ProxyUriParseError, parse_proxy_link
from app.services.copilot.tools import execute_tool
from tests.api import GetTestDB

VLESS_LINK = (
    "vless://0373083d-5359-449f-815d-79f0e881c2bf@example.com:443"
    "?encryption=none&security=tls&sni=sni.example&type=ws&path=/ws#France"
)


def _vmess_link(**overrides) -> str:
    payload = {
        "v": "2",
        "ps": "VMessTest",
        "add": "example.com",
        "port": "443",
        "id": "11111111-1111-1111-1111-111111111111",
        "aid": "0",
        "net": "ws",
        "type": "none",
        "host": "host.example",
        "path": "/vmess",
        "tls": "tls",
        "sni": "sni.example",
    }
    payload.update(overrides)
    token = base64.b64encode(json.dumps(payload).encode()).decode()
    return f"vmess://{token}"


def test_parse_vmess_link():
    parsed = parse_proxy_link(_vmess_link())

    assert parsed.protocol == "vmess"
    assert parsed.address == "example.com"
    assert parsed.port == 443
    assert parsed.client_id == "11111111-1111-1111-1111-111111111111"
    assert parsed.network == "ws"
    assert parsed.security == "tls"
    assert parsed.sni == "sni.example"
    assert parsed.host_header == "host.example"
    assert parsed.path == "/vmess"
    assert parsed.remark == "VMessTest"


def test_parse_trojan_link():
    link = "trojan://secret-pass@example.com:8443?security=tls&sni=sni.example&type=ws&path=/trojan#TrojanTest"
    parsed = parse_proxy_link(link)

    assert parsed.protocol == "trojan"
    assert parsed.password == "secret-pass"
    assert parsed.port == 8443
    assert parsed.security == "tls"
    assert parsed.network == "ws"
    assert parsed.remark == "TrojanTest"


def test_parse_shadowsocks_sip002_link():
    creds = base64.urlsafe_b64encode(b"aes-256-gcm:password").decode().rstrip("=")
    link = f"ss://{creds}@example.com:8388#SS-Test"
    parsed = parse_proxy_link(link)

    assert parsed.protocol == "shadowsocks"
    assert parsed.address == "example.com"
    assert parsed.port == 8388
    assert parsed.password == "password"
    assert parsed.extra["method"] == "aes-256-gcm"
    assert parsed.remark == "SS-Test"


def test_parse_proxy_link_rejects_unknown_scheme():
    with pytest.raises(ProxyUriParseError, match="Unsupported link scheme"):
        parse_proxy_link("http://example.com")


def test_suggest_inbound_tags_prefers_protocol_and_network():
    parsed = parse_proxy_link(VLESS_LINK)
    inbounds = [
        {"tag": "other", "protocol": "vmess", "network": "tcp", "port": 443},
        {"tag": "match", "protocol": "vless", "network": "ws", "port": 443},
        {"tag": "proto-only", "protocol": "vless", "network": "tcp", "port": 80},
    ]

    suggestions = suggest_inbound_tags(parsed, inbounds)

    assert suggestions[0] == "match"
    assert "proto-only" in suggestions


def test_preview_host_import_includes_ready_fields():
    parsed = parse_proxy_link(VLESS_LINK)
    preview = preview_host_import(parsed, inbound_tag="VLESS-WS", priority=1)

    assert preview["parsed"]["protocol"] == "vless"
    assert preview["host"]["inbound_tag"] == "VLESS-WS"
    assert preview["host"]["remark"] == "France"
    assert "notes" in preview


@pytest.mark.asyncio
async def test_import_proxy_link_auto_inbound_preview():
    async with GetTestDB() as db:
        admin = await get_admin(db, "testadmin", load_users=False, load_usage_logs=False)
        result = await import_proxy_link(db, admin=admin, link=VLESS_LINK, inbound_tag="", confirm=False)

    if result.get("error"):
        assert "suggested_inbound_tags" in result
        return

    assert result.get("ready") is True
    assert result["host"]["inbound_tag"]
    assert "inbound" in result


@pytest.mark.asyncio
async def test_execute_tool_import_proxy_link_permission_denied():
    from app.models.admin import AdminDetails

    read_only = AdminDetails(
        id=99,
        username="readonly",
        role={"permissions": {"hosts": {"read": True}}, "is_owner": False, "limits": {}, "features": {}, "access": {}},
    )

    async with GetTestDB() as db:
        preview, _ = await execute_tool(
            db,
            admin=read_only,
            name="import_proxy_link",
            arguments={"link": VLESS_LINK, "confirm": False},
        )
        denied, _ = await execute_tool(
            db,
            admin=read_only,
            name="import_proxy_link",
            arguments={"link": VLESS_LINK, "confirm": True},
        )

    assert preview.get("ready") is True
    assert "error" in denied
    assert "Permission" in denied["error"]
