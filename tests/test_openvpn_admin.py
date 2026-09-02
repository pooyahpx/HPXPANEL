from unittest.mock import AsyncMock, patch

from app.models.proxy import OpenVPNSettings, ProxyTable


def test_renew_openvpn_certificate_endpoint(client, access_token, test_user):
    fake_user = {"id": test_user["id"], "username": test_user["username"]}
    with patch(
        "app.routers.user.user_operator.renew_openvpn_cert_by_id",
        new=AsyncMock(return_value=fake_user),
    ):
        response = client.post(
            f"/api/user/by-id/{test_user['id']}/openvpn/renew",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    assert response.status_code == 200


def test_revoke_openvpn_certificate_endpoint(client, access_token, test_user):
    fake_user = {"id": test_user["id"], "username": test_user["username"]}
    with patch(
        "app.routers.user.user_operator.revoke_openvpn_cert_by_id",
        new=AsyncMock(return_value=fake_user),
    ):
        response = client.post(
            f"/api/user/by-id/{test_user['id']}/openvpn/revoke-cert",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    assert response.status_code == 200


def test_clear_openvpn_credentials():
    from app.utils.openvpn import clear_openvpn_credentials

    proxy = ProxyTable()
    proxy.openvpn = OpenVPNSettings(
        serial="abc",
        fingerprint="def",
        client_cert="cert",
        client_key="key",
    )
    cleared = clear_openvpn_credentials(proxy)
    assert cleared.openvpn.serial == ""
    assert cleared.openvpn.client_cert == ""
