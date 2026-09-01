import json

import pytest

from app.core.openvpn import OpenVPNConfig
from app.db.models import CoreType
from app.models.protocol import ProxyProtocol
from app.models.proxy import ProxyTable

OPENVPN_REQUIRED = {
    "inbound_tag": "ovpn-main",
    "port": 1194,
    "server_subnet": "10.29.0.0/16",
    "ca_cert": "CA PEM",
    "server_cert": "SERVER PEM",
    "server_key": "KEY PEM",
}


def test_openvpn_config_applies_node_defaults_and_builds_inbound_metadata():
    config = OpenVPNConfig(OPENVPN_REQUIRED)

    assert config.type == CoreType.openvpn
    assert config["proto"] == "udp"
    assert config["device"] == "tun"
    assert config["cipher"] == "AES-256-GCM"
    assert config["auth"] == "SHA256"
    assert config["keepalive"] == "10 60"
    assert config["max_clients"] == 1024
    assert config["dns"] == ["1.1.1.1", "8.8.8.8"]
    assert config.inbounds == ["ovpn-main"]
    assert config.inbounds_by_tag["ovpn-main"]["protocol"] == "openvpn"
    assert config.protocols == frozenset((ProxyProtocol.openvpn,))
    assert json.loads(config.to_str())["server_subnet"] == "10.29.0.0/16"


@pytest.mark.parametrize("field", ["inbound_tag", "port", "server_subnet", "ca_cert", "server_cert", "server_key"])
def test_openvpn_config_rejects_missing_required_fields(field: str):
    payload = dict(OPENVPN_REQUIRED)
    payload.pop(field)

    with pytest.raises(ValueError, match=field):
        OpenVPNConfig(payload)


def test_openvpn_config_normalizes_listeners():
    config = OpenVPNConfig(
        {
            **OPENVPN_REQUIRED,
            "listeners": [{"port": 1194, "proto": "udp"}, {"port": 443, "proto": "tcp"}],
        }
    )

    assert config["listeners"] == [{"port": 1194, "proto": "udp"}, {"port": 443, "proto": "tcp"}]


def test_openvpn_config_rejects_duplicate_listeners():
    with pytest.raises(ValueError, match="duplicate listener"):
        OpenVPNConfig(
            {
                **OPENVPN_REQUIRED,
                "listeners": [{"port": 1194, "proto": "udp"}, {"port": 1194, "proto": "udp"}],
            }
        )


def test_openvpn_config_json_round_trip():
    original = OpenVPNConfig(OPENVPN_REQUIRED)
    restored = OpenVPNConfig.from_json(original.to_json())

    assert restored.type == original.type
    assert restored == original
    assert restored.inbounds == original.inbounds
    assert restored.inbounds_by_tag == original.inbounds_by_tag
    assert restored.protocols == original.protocols


def test_proxy_table_includes_openvpn_defaults():
    proxy = ProxyTable.model_validate({"vmess": {"id": "5cd987b9-e28d-4673-ae31-0c251310f965"}})
    dumped = proxy.dict()

    assert dumped["openvpn"]["serial"] == ""
    assert dumped["openvpn"]["fingerprint"] == ""


def test_protocol_enum_values_are_append_only():
    assert ProxyProtocol.openvpn.value == 9
