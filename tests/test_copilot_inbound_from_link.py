from app.services.copilot.inbound_from_link import (
    build_xray_inbound_from_link,
    default_inbound_tag,
    inbound_matches_link,
    unique_inbound_tag,
)
from app.services.copilot.proxy_uri import parse_proxy_link

VLESS_WS = (
    "vless://0373083d-5359-449f-815d-79f0e881c2bf@185.143.233.235:8080"
    "?encryption=none&security=none&type=ws&host=lolz.nerixa.ir&path=%2Fg4XasaX#SPECIAL"
)


def test_build_xray_inbound_vless_ws():
    parsed = parse_proxy_link(VLESS_WS)
    inbound = build_xray_inbound_from_link(parsed, tag="SPECIAL")

    assert inbound["tag"] == "SPECIAL"
    assert inbound["port"] == 8080
    assert inbound["protocol"] == "vless"
    assert inbound["streamSettings"]["network"] == "ws"
    assert inbound["streamSettings"]["security"] == "none"
    assert inbound["streamSettings"]["wsSettings"]["path"] == "/g4XasaX"
    assert inbound["streamSettings"]["wsSettings"]["host"] == "lolz.nerixa.ir"


def test_inbound_matches_link():
    parsed = parse_proxy_link(VLESS_WS)
    inbound = build_xray_inbound_from_link(parsed, tag="x")
    assert inbound_matches_link(inbound, parsed) is True

    other = dict(inbound)
    other["port"] = 443
    assert inbound_matches_link(other, parsed) is False


def test_default_inbound_tag_uses_remark():
    parsed = parse_proxy_link(VLESS_WS)
    assert default_inbound_tag(parsed) == "SPECIAL"


def test_unique_inbound_tag_suffix():
    assert unique_inbound_tag({"SPECIAL"}, "SPECIAL") == "SPECIAL (2)"
