import pytest

from app.services.copilot.proxy_uri import ProxyUriParseError, parse_proxy_link


def test_parse_vless_ws_tls_link():
    link = (
        "vless://0373083d-5359-449f-815d-79f0e881c2bf@542ba-8495-4080-be53-f311a476.vidboxco.ir:3344"
        "?encryption=none&security=tls&sni=w.wizardxray.net&insecure=0&allowInsecure=0&type=ws"
        "&path=%2F%3Fed%3D2048#%F0%9F%87%AB%F0%9F%87%B7%20France"
    )
    parsed = parse_proxy_link(link)

    assert parsed.protocol == "vless"
    assert parsed.client_id == "0373083d-5359-449f-815d-79f0e881c2bf"
    assert parsed.address == "542ba-8495-4080-be53-f311a476.vidboxco.ir"
    assert parsed.port == 3344
    assert parsed.security == "tls"
    assert parsed.network == "ws"
    assert parsed.sni == "w.wizardxray.net"
    assert parsed.path == "/?ed=2048"
    assert parsed.allow_insecure is False
    assert "France" in parsed.remark


def test_build_create_host_from_vless_link():
    from app.services.copilot.host_import import build_create_host_from_link

    parsed = parse_proxy_link(
        "vless://11111111-1111-1111-1111-111111111111@example.com:443?security=tls&type=ws&path=/ws&sni=sni.example#Test"
    )
    host = build_create_host_from_link(parsed, inbound_tag="VLESS-WS", priority=3)

    assert host.remark == "Test"
    assert host.inbound_tag == "VLESS-WS"
    assert host.port == 443
    assert "example.com" in host.address
    assert host.sni == {"sni.example"}
    assert host.path == "/ws"
    assert host.priority == 3
    assert host.transport_settings is not None
    assert host.transport_settings.websocket_settings is not None


def test_parse_vless_rejects_missing_port():
    with pytest.raises(ProxyUriParseError, match="host and port"):
        parse_proxy_link("vless://uuid@example.com?type=ws")


def test_parse_vmess_rejects_invalid_payload():
    with pytest.raises(ProxyUriParseError, match="Invalid vmess"):
        parse_proxy_link("vmess://not-valid-base64!!!")
