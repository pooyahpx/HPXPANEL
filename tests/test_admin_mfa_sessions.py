"""Tests for admin TOTP MFA enrollment and session revoke."""

from __future__ import annotations

import asyncio

import pyotp
import pytest
from fastapi import status
from sqlalchemy import select

from app.db.models import Admin, AdminSession
from app.utils.crypto import decrypt_secret
from app.utils.jwt import get_secret_key
from tests.api import TestSession, client
from tests.api.helpers import auth_headers, create_admin, delete_admin, strong_password, unique_name


@pytest.fixture
def access_token() -> str:
    response = client.post(
        url="/api/admin/token",
        data={"username": "testadmin", "password": "testadmin", "grant_type": "password"},
    )
    return response.json()["access_token"]


def _login(username: str, password: str):
    return client.post(
        "/api/admin/token",
        data={"username": username, "password": password, "grant_type": "password"},
    )


def _enable_totp(token: str) -> str:
    setup = client.post("/api/admin/security/totp/setup", headers=auth_headers(token))
    assert setup.status_code == status.HTTP_200_OK, setup.text
    secret = setup.json()["secret"]
    code = pyotp.TOTP(secret).now()
    confirm = client.post(
        "/api/admin/security/totp/confirm",
        headers=auth_headers(token),
        json={"code": code},
    )
    assert confirm.status_code == status.HTTP_200_OK, confirm.text
    assert confirm.json()["totp_enabled"] is True
    return secret


@pytest.fixture
def mfa_admin(access_token):
    admin = create_admin(access_token, username=unique_name("mfa"), password=strong_password("MfaAdmin"))
    try:
        login = _login(admin["username"], admin["password"])
        assert login.status_code == status.HTTP_200_OK
        admin_token = login.json()["access_token"]
        yield {**admin, "token": admin_token}
    finally:
        delete_admin(access_token, admin["username"])


def test_totp_enroll_and_confirm_enables(mfa_admin):
    secret = _enable_totp(mfa_admin["token"])
    assert secret

    async def _assert_encrypted_secret():
        async with TestSession() as session:
            db_admin = (
                await session.execute(select(Admin).where(Admin.username == mfa_admin["username"]))
            ).scalar_one()
            assert db_admin.totp_enabled is True
            assert db_admin.totp_secret
            assert db_admin.totp_secret != secret
            decrypted = decrypt_secret(db_admin.totp_secret, await get_secret_key())
            assert decrypted == secret

    asyncio.run(_assert_encrypted_secret())


def test_login_without_code_returns_mfa_required(mfa_admin):
    _enable_totp(mfa_admin["token"])

    response = _login(mfa_admin["username"], mfa_admin["password"])
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["mfa_required"] is True
    assert data["mfa_token"]
    assert data.get("access_token") in ("", None)


def test_login_with_mfa_code_issues_token(mfa_admin):
    secret = _enable_totp(mfa_admin["token"])

    challenge = _login(mfa_admin["username"], mfa_admin["password"])
    assert challenge.status_code == status.HTTP_200_OK
    mfa_token = challenge.json()["mfa_token"]

    response = client.post(
        "/api/admin/token/mfa",
        json={"mfa_token": mfa_token, "code": pyotp.TOTP(secret).now()},
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["access_token"]
    assert data.get("mfa_required") is False

    me = client.get("/api/admin", headers=auth_headers(data["access_token"]))
    assert me.status_code == status.HTTP_200_OK
    assert me.json()["username"] == mfa_admin["username"]


def test_revoke_session_blocks_auth(mfa_admin):
    login = _login(mfa_admin["username"], mfa_admin["password"])
    assert login.status_code == status.HTTP_200_OK
    token = login.json()["access_token"]

    me = client.get("/api/admin", headers=auth_headers(token))
    assert me.status_code == status.HTTP_200_OK

    sessions = client.get("/api/admin/security/sessions", headers=auth_headers(token))
    assert sessions.status_code == status.HTTP_200_OK
    session_list = sessions.json()["sessions"]
    assert len(session_list) >= 1
    current = next(s for s in session_list if s["current"])

    revoke = client.delete(f"/api/admin/security/sessions/{current['id']}", headers=auth_headers(token))
    assert revoke.status_code == status.HTTP_204_NO_CONTENT

    blocked = client.get("/api/admin", headers=auth_headers(token))
    assert blocked.status_code == status.HTTP_401_UNAUTHORIZED

    async def _assert_revoked():
        async with TestSession() as session:
            row = (
                await session.execute(select(AdminSession).where(AdminSession.id == current["id"]))
            ).scalar_one()
            assert row.revoked_at is not None

    asyncio.run(_assert_revoked())
