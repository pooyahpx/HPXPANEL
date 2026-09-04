from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.metrics import router
from config import observability_settings


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_metrics_accepts_configured_bearer_token(monkeypatch):
    monkeypatch.setattr(observability_settings, "metrics_token", "metrics-secret")
    monkeypatch.setattr(observability_settings, "metrics_allow_unauthenticated", False)

    response = _client().get("/metrics", headers={"Authorization": "Bearer metrics-secret"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")


def test_metrics_rejects_missing_or_wrong_bearer_token(monkeypatch):
    monkeypatch.setattr(observability_settings, "metrics_token", "metrics-secret")
    monkeypatch.setattr(observability_settings, "metrics_allow_unauthenticated", True)
    client = _client()

    missing = client.get("/metrics")
    wrong = client.get("/metrics", headers={"Authorization": "Bearer wrong-secret"})

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"


def test_metrics_without_token_is_unavailable_by_default(monkeypatch):
    monkeypatch.setattr(observability_settings, "metrics_token", "")
    monkeypatch.setattr(observability_settings, "metrics_allow_unauthenticated", False)

    response = _client().get("/metrics")

    assert response.status_code == 503
    assert "OBSERVABILITY_METRICS_TOKEN" in response.json()["detail"]


def test_metrics_can_explicitly_allow_unauthenticated_access(monkeypatch):
    monkeypatch.setattr(observability_settings, "metrics_token", "")
    monkeypatch.setattr(observability_settings, "metrics_allow_unauthenticated", True)

    response = _client().get("/metrics")

    assert response.status_code == 200
