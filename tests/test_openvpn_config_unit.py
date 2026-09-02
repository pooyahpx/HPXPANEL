from app.models.subscription import SubscriptionInboundData, TCPTransportConfig, TLSConfig
from app.subscription.openvpn import OpenVPNConfiguration


def test_openvpn_configuration_renders_client_profile():
    inbound = SubscriptionInboundData(
        remark="Test Host",
        inbound_tag="ovpn-main",
        protocol="openvpn",
        address="203.0.113.1",
        port=1194,
        network="udp",
        tls_config=TLSConfig(),
        transport_config=TCPTransportConfig(path="", host=[]),
        openvpn_ca_cert="-----BEGIN CERTIFICATE-----\nCA\n-----END CERTIFICATE-----\n",
        openvpn_tls_crypt_key="-----BEGIN OpenVPN Static key V1-----\nKEY\n-----END OpenVPN Static key V1-----\n",
        openvpn_cipher="AES-256-GCM",
        openvpn_auth="SHA256",
        openvpn_proto="udp",
        openvpn_device="tun",
        openvpn_dns=["1.1.1.1"],
    )
    settings = {
        "client_cert": "-----BEGIN CERTIFICATE-----\nCLIENT\n-----END CERTIFICATE-----\n",
        "client_key": "-----BEGIN PRIVATE KEY-----\nKEY\n-----END PRIVATE KEY-----\n",
    }

    conf = OpenVPNConfiguration()
    conf.add("Test Host", "203.0.113.1", inbound, settings)
    body = conf.render().decode()

    assert "client" in body
    assert "remote 203.0.113.1 1194" in body
    assert "<ca>" in body
    assert "<cert>" in body
    assert "<key>" in body
    assert "<tls-crypt>" in body
    assert "dhcp-option DNS 1.1.1.1" in body


def test_openvpn_configuration_merges_multiple_hosts_into_one_profile():
    inbound = SubscriptionInboundData(
        remark="Test Host",
        inbound_tag="ovpn-main",
        protocol="openvpn",
        address="203.0.113.1",
        port=1194,
        network="udp",
        tls_config=TLSConfig(),
        transport_config=TCPTransportConfig(path="", host=[]),
        openvpn_ca_cert="-----BEGIN CERTIFICATE-----\nCA\n-----END CERTIFICATE-----\n",
        openvpn_cipher="AES-256-GCM",
        openvpn_auth="SHA256",
        openvpn_proto="udp",
        openvpn_device="tun",
    )
    settings = {
        "client_cert": "-----BEGIN CERTIFICATE-----\nCLIENT\n-----END CERTIFICATE-----\n",
        "client_key": "-----BEGIN PRIVATE KEY-----\nKEY\n-----END PRIVATE KEY-----\n",
    }

    conf = OpenVPNConfiguration()
    conf.add("Host A", "203.0.113.1", inbound, settings)
    conf.add("Host B", "203.0.113.2", inbound, settings)
    body = conf.render()

    assert body[:2] != b"PK"
    text = body.decode()
    assert text.count("remote ") == 2
    assert "remote 203.0.113.1 1194" in text
    assert "remote 203.0.113.2 1194" in text
