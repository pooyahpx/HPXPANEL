import pytest
from fastapi import status

from app.rate_limit import InMemoryRateLimitBackend, rate_limiter
from config import rate_limit_settings
from tests.api import client


@pytest.fixture(autouse=True)
def enable_fresh_rate_limiter(monkeypatch):
    monkeypatch.setattr(rate_limit_settings, "enabled", True)
    rate_limiter.set_backend_for_testing(InMemoryRateLimitBackend(max_keys=100))


def _password_login(username: str):
    return client.post(
        "/api/admin/token",
        data={"username": username, "password": "wrong", "grant_type": "password"},
    )


def test_admin_login_same_identity_keeps_configured_limit(monkeypatch):
    monkeypatch.setattr(rate_limit_settings, "admin_login_limit", 2)

    assert _password_login("missing-admin").status_code == status.HTTP_401_UNAUTHORIZED
    assert _password_login("missing-admin").status_code == status.HTTP_401_UNAUTHORIZED
    response = _password_login("missing-admin")
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.headers["Retry-After"]


def test_admin_login_username_rotation_hits_client_bucket(monkeypatch):
    monkeypatch.setattr(rate_limit_settings, "admin_login_limit", 2)

    assert _password_login("missing-one").status_code == status.HTTP_401_UNAUTHORIZED
    assert _password_login("missing-two").status_code == status.HTTP_401_UNAUTHORIZED
    assert _password_login("missing-three").status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_miniapp_login_token_rotation_hits_client_bucket(monkeypatch):
    monkeypatch.setattr(rate_limit_settings, "admin_login_limit", 2)

    first = client.post("/api/admin/miniapp/token", headers={"X-Telegram-Authorization": "token-one"})
    second = client.post("/api/admin/miniapp/token", headers={"X-Telegram-Authorization": "token-two"})
    assert first.status_code != status.HTTP_429_TOO_MANY_REQUESTS
    assert second.status_code != status.HTTP_429_TOO_MANY_REQUESTS
    response = client.post("/api/admin/miniapp/token", headers={"X-Telegram-Authorization": "token-three"})
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.parametrize(
    ("method", "url", "kwargs"),
    [
        (
            "POST",
            "/api/setup/owner",
            {
                "json": {
                    "key": "00000000-0000-0000-0000-000000000000",
                    "username": "new-owner",
                    "password": "OwnerPass#12ab",
                }
            },
        ),
        (
            "PATCH",
            "/api/setup/owner",
            {
                "json": {
                    "key": "00000000-0000-0000-0000-000000000001",
                    "password": "NewOwnerPass#34cd",
                }
            },
        ),
        (
            "DELETE",
            "/api/setup/owner",
            {"params": {"key": "00000000-0000-0000-0000-000000000002"}},
        ),
        (
            "POST",
            "/api/setup/owner/upgrade",
            {
                "json": {
                    "key": "00000000-0000-0000-0000-000000000003",
                    "username": "missing-admin",
                }
            },
        ),
    ],
)
def test_every_owner_mutation_is_rate_limited(monkeypatch, method, url, kwargs):
    monkeypatch.setattr(rate_limit_settings, "setup_limit", 1)

    assert client.request(method, url, **kwargs).status_code != status.HTTP_429_TOO_MANY_REQUESTS
    response = client.request(method, url, **kwargs)
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.headers["Retry-After"]


def test_pulse_claim_route_is_rate_limited(monkeypatch):
    monkeypatch.setattr(rate_limit_settings, "pulse_claim_limit", 1)
    body = {"join_token": "missing-token", "host": "agent.example", "side": "iran"}
    assert client.post("/api/hpx_pulse/agent/claim", json=body).status_code != status.HTTP_429_TOO_MANY_REQUESTS
    assert client.post("/api/hpx_pulse/agent/claim", json=body).status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_subscription_routes_share_a_rate_limit(monkeypatch):
    monkeypatch.setattr(rate_limit_settings, "subscription_limit", 1)
    assert client.get("/sub/missing-token").status_code != status.HTTP_429_TOO_MANY_REQUESTS
    response = client.get("/sub/missing-token/info")
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.headers["Retry-After"]
