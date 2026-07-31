import json

import pytest

from app.core.ikev2 import IKEv2Config
from app.core.l2tp import L2TPConfig
from app.db.models import CoreType
from app.models.protocol import ProxyProtocol
from app.models.proxy import ProxyTable

IKEV2_REQUIRED = {
    "inbound_tag": "ike-main",
    "server_addr": "vpn.example.com",
    "pool": "10.30.0.12/24",
    "ca_cert": "CA PEM",
    "server_cert": "SERVER PEM",
    "server_key": "KEY PEM",
}

L2TP_REQUIRED = {
    "inbound_tag": "l2tp-main",
    "psk": "a sufficiently secret PSK",
    "pool": "10.31.0.0/24",
}


def test_ikev2_config_applies_node_defaults_and_builds_inbound_metadata():
    config = IKEv2Config(IKEV2_REQUIRED)

    assert config.type == CoreType.ikev2
    assert config["pool"] == "10.30.0.0/24"
    assert config["identity"] == "vpn.example.com"
    assert config["dns"] == ["1.1.1.1", "8.8.8.8"]
    assert config["ike_proposals"] == ["aes256-sha256-modp2048", "aes128-sha256-modp2048"]
    assert config["esp_proposals"] == ["aes256-sha256", "aes128-sha256"]
    assert config.inbounds == ["ike-main"]
    assert config.inbounds_by_tag["ike-main"]["protocol"] == "ikev2"
    assert config.protocols == frozenset((ProxyProtocol.ikev2,))
    assert json.loads(config.to_str())["ca_cert"] == "CA PEM"


@pytest.mark.parametrize("field", ["inbound_tag", "server_addr", "pool", "ca_cert", "server_cert", "server_key"])
def test_ikev2_config_rejects_missing_required_fields(field: str):
    payload = dict(IKEV2_REQUIRED)
    payload.pop(field)

    with pytest.raises(ValueError, match=field):
        IKEv2Config(payload)


def test_l2tp_config_applies_node_defaults_and_reuses_logical_protocol():
    config = L2TPConfig(L2TP_REQUIRED)

    assert config.type == CoreType.l2tp
    assert config["local_ip"] == "10.31.0.1"
    assert config["server_addr"] == ""
    assert config["ike_proposals"] == [
        "aes256-sha1-modp2048",
        "aes128-sha1-modp1024",
        "3des-sha1-modp1024",
    ]
    assert config["esp_proposals"] == ["aes256-sha1", "aes128-sha1", "3des-sha1"]
    assert config.inbounds_by_tag["l2tp-main"]["protocol"] == "l2tp"
    assert config.protocols == frozenset((ProxyProtocol.l2tp,))


@pytest.mark.parametrize("field", ["inbound_tag", "psk", "pool"])
def test_l2tp_config_rejects_missing_required_fields(field: str):
    payload = dict(L2TP_REQUIRED)
    payload.pop(field)

    with pytest.raises(ValueError, match=field):
        L2TPConfig(payload)


@pytest.mark.parametrize(
    ("config_type", "payload"),
    [(IKEv2Config, IKEV2_REQUIRED), (L2TPConfig, L2TP_REQUIRED)],
)
def test_ipsec_config_json_round_trip(config_type, payload):
    original = config_type(payload)
    restored = config_type.from_json(original.to_json())

    assert restored.type == original.type
    assert restored == original
    assert restored.inbounds == original.inbounds
    assert restored.inbounds_by_tag == original.inbounds_by_tag
    assert restored.protocols == original.protocols


def test_proxy_table_adds_stable_ikev2_defaults_to_existing_json():
    proxy = ProxyTable.model_validate({"vmess": {"id": "5cd987b9-e28d-4673-ae31-0c251310f965"}})
    dumped = proxy.dict()

    assert dumped["ikev2"]["username"]
    assert dumped["ikev2"]["password"]
    assert proxy.l2tp is proxy.ikev2
    assert "l2tp" not in dumped
    assert ProxyTable.model_validate(dumped).ikev2 == proxy.ikev2


def test_protocol_enum_values_are_append_only():
    assert ProxyProtocol.ikev2.value == 7
    assert ProxyProtocol.l2tp.value == 8
