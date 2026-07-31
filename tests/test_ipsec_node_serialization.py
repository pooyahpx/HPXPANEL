import pytest

pytest.importorskip("PasarGuardNodeBridge", reason="node bridge is not installed")

from PasarGuardNodeBridge.common import service_pb2 as service

_HAS_UPGRADED_BRIDGE = (
    "ikev2" in service.Proxy.DESCRIPTOR.fields_by_name
    and "ip_limit" in service.User.DESCRIPTOR.fields_by_name
    and "speed_limit" in service.User.DESCRIPTOR.fields_by_name
)

if not _HAS_UPGRADED_BRIDGE:
    pytest.skip(
        "installed node bridge does not yet expose IKEv2 credentials and user limits",
        allow_module_level=True,
    )

from app.models.protocol import ProxyProtocol
from app.node.user import _serialize_user_for_node


@pytest.mark.parametrize("protocol", [ProxyProtocol.ikev2, ProxyProtocol.l2tp])
def test_ipsec_user_serialization_reuses_ikev2_credentials_and_limits(protocol):
    user = _serialize_user_for_node(
        42,
        {"ikev2": {"username": "native-user", "password": "native-password"}},
        ["native-inbound"],
        frozenset((protocol,)),
        ip_limit=3,
        speed_limit=0,
    )

    assert user.email == "42"
    assert user.inbounds == ["native-inbound"]
    assert user.proxies.ikev2.username == "native-user"
    assert user.proxies.ikev2.password == "native-password"
    assert user.ip_limit == 3
    assert user.speed_limit == 0
