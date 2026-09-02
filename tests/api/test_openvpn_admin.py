from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from app.db.models import UserStatus
from app.models.proxy import OpenVPNSettings, ProxyTable
from app.models.user import UserResponse
from tests.api import client


def _fake_user_response() -> UserResponse:
    return UserResponse(
        id=1,
        username="testuser",
        status=UserStatus.active,
        used_traffic=0,
        created_at=datetime.now(UTC),
    )


def test_renew_openvpn_certificate_endpoint(access_token):
    with patch(
        "app.routers.user.user_operator.renew_openvpn_cert_by_id",
        new=AsyncMock(return_value=_fake_user_response()),
    ):
        response = client.post(
            "/api/user/by-id/1/openvpn/renew",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    assert response.status_code == 200


def test_revoke_openvpn_certificate_endpoint(access_token):
    with patch(
        "app.routers.user.user_operator.revoke_openvpn_cert_by_id",
        new=AsyncMock(return_value=_fake_user_response()),
    ):
        response = client.post(
            "/api/user/by-id/1/openvpn/revoke-cert",
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
