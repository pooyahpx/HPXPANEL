import pytest

pytest.importorskip("PasarGuardNodeBridge", reason="node bridge is not installed")

from PasarGuardNodeBridge.common import service_pb2 as service

_HAS_OPENVPN_BRIDGE = "openvpn" in service.Proxy.DESCRIPTOR.fields_by_name

if not _HAS_OPENVPN_BRIDGE:
    pytest.skip(
        "installed node bridge does not yet expose OpenVPN credentials",
        allow_module_level=True,
    )

from app.models.protocol import ProxyProtocol
from app.node.user import _serialize_user_for_node


def test_openvpn_user_serialization_includes_serial_and_fingerprint():
    user = _serialize_user_for_node(
        42,
        {"openvpn": {"serial": "ABC123", "fingerprint": "sha256:deadbeef"}},
        ["ovpn-main"],
        frozenset((ProxyProtocol.openvpn,)),
        ip_limit=2,
    )

    assert user.email == "42"
    assert user.inbounds == ["ovpn-main"]
    assert user.proxies.openvpn.serial == "ABC123"
    assert user.proxies.openvpn.fingerprint == "sha256:deadbeef"


def test_openvpn_user_serialization_allows_empty_serial():
    user = _serialize_user_for_node(
        7,
        {"openvpn": {"serial": "", "fingerprint": ""}},
        ["ovpn-main"],
        frozenset((ProxyProtocol.openvpn,)),
    )

    assert user.proxies.openvpn.serial == ""
    assert user.proxies.openvpn.fingerprint == ""
