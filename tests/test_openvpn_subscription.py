import zipfile
from io import BytesIO

from fastapi import status

from tests.api import client
from tests.api.helpers import (
    auth_headers,
    create_core,
    create_group,
    create_user,
    delete_core,
    delete_group,
    delete_user,
    unique_name,
)


def test_openvpn_subscription_download(access_token):
    pki_response = client.post(
        "/api/core/openvpn/generate-pki",
        headers=auth_headers(access_token),
        json={},
    )
    assert pki_response.status_code == status.HTTP_200_OK
    pki = pki_response.json()

    inbound_tag = unique_name("ovpn_sub")
    endpoint = "203.0.113.10"
    core = create_core(
        access_token,
        name=unique_name("openvpn_subscription_core"),
        config={
            "inbound_tag": inbound_tag,
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

    host_response = client.post(
        "/api/host",
        headers=auth_headers(access_token),
        json={
            "remark": "OVPN {USERNAME}",
            "address": [endpoint],
            "port": 1194,
            "inbound_tag": inbound_tag,
            "priority": 1,
        },
    )
    assert host_response.status_code == status.HTTP_201_CREATED
    host_id = host_response.json()["id"]

    group = create_group(access_token, name=unique_name("openvpn_subscription_group"), inbound_tags=[inbound_tag])
    user = create_user(access_token, group_ids=[group["id"]], payload={"username": unique_name("ovpn_user")})

    try:
        openvpn_settings = user["proxy_settings"]["openvpn"]
        assert openvpn_settings["client_cert"].startswith("-----BEGIN CERTIFICATE-----")
        assert openvpn_settings["client_key"].startswith("-----BEGIN")
        assert openvpn_settings["serial"]
        assert openvpn_settings["fingerprint"].startswith("sha256:")

        response = client.get(f"{user['subscription_url']}/openvpn")
        assert response.status_code == status.HTTP_200_OK

        content_type = response.headers.get("content-type", "")
        body = response.content

        if "zip" in content_type:
            with zipfile.ZipFile(BytesIO(body)) as archive:
                names = archive.namelist()
                assert names
                config_text = archive.read(names[0]).decode()
        else:
            config_text = body.decode()

        assert "client" in config_text
        assert f"remote {endpoint} 1194" in config_text
        assert "<ca>" in config_text
        assert "<cert>" in config_text
        assert "<key>" in config_text
        assert openvpn_settings["client_cert"].strip() in config_text
        assert pki["ca_cert"].strip() in config_text
        assert pki["tls_crypt_key"].strip() in config_text
    finally:
        delete_user(access_token, user["username"])
        delete_group(access_token, group["id"])
        client.delete(f"/api/host/{host_id}", headers=auth_headers(access_token))
        delete_core(access_token, core["id"])
