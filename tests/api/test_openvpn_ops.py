from fastapi import status

from tests.api import client
from tests.api.helpers import auth_headers, create_core, delete_core, unique_name


def test_openvpn_core_rejects_missing_ca_key(access_token):
    inbound_tag = unique_name("ovpn_ca")
    response = client.post(
        "/api/core",
        headers=auth_headers(access_token),
        json={
            "name": unique_name("openvpn_missing_ca"),
            "type": "openvpn",
            "config": {
                "inbound_tag": inbound_tag,
                "port": 1194,
                "proto": "udp",
                "server_subnet": "10.29.0.0/16",
                "dns": ["1.1.1.1"],
                "ca_cert": "-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----",
                "server_cert": "-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----",
                "server_key": "-----BEGIN PRIVATE KEY-----\nTEST\n-----END PRIVATE KEY-----",
            },
            "exclude_inbound_tags": [],
            "fallbacks_inbound_tags": [],
        },
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "ca_key" in response.json()["detail"].lower()


def test_openvpn_health_endpoint(access_token):
    pki_response = client.post(
        "/api/core/openvpn/generate-pki",
        headers=auth_headers(access_token),
        json={},
    )
    assert pki_response.status_code == status.HTTP_200_OK
    pki = pki_response.json()
    core = create_core(
        access_token,
        name=unique_name("openvpn_health_core"),
        config={
            "inbound_tag": unique_name("ovpn_health"),
            "port": 1194,
            "proto": "udp",
            "server_subnet": "10.29.0.0/16",
            "dns": ["1.1.1.1"],
            "ca_cert": pki["ca_cert"],
            "ca_key": pki["ca_key"],
            "server_cert": pki["server_cert"],
            "server_key": pki["server_key"],
            "tls_crypt_key": pki["tls_crypt_key"],
        },
        type="openvpn",
        fallbacks=[],
    )
    try:
        health = client.get(
            f"/api/openvpn/health?core_id={core['id']}",
            headers=auth_headers(access_token),
        )
        assert health.status_code == status.HTTP_200_OK
        body = health.json()
        assert body["pki_ready"] is True
        assert body["ca_key_missing"] is False
    finally:
        delete_core(access_token, core["id"])
