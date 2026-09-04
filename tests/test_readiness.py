import json

import pytest

from app.routers import home
from role import Role


class HealthyDB:
    async def execute(self, _query):
        return None


class BrokenDB:
    async def execute(self, _query):
        raise RuntimeError("database offline")


@pytest.mark.asyncio
async def test_health_remains_liveness_only():
    assert await home.health() == {"status": "ok"}


@pytest.mark.asyncio
async def test_ready_without_nats_checks_database(monkeypatch):
    monkeypatch.setattr(home, "is_nats_enabled", lambda: False)

    response = await home.ready(HealthyDB())

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "status": "ready",
        "checks": {"database": {"status": "ok"}, "nats": {"status": "disabled"}},
    }


@pytest.mark.asyncio
async def test_ready_returns_503_when_database_is_down(monkeypatch):
    monkeypatch.setattr(home, "is_nats_enabled", lambda: False)

    response = await home.ready(BrokenDB())

    assert response.status_code == 503
    body = json.loads(response.body)
    assert body["status"] == "not_ready"
    assert body["checks"]["database"]["status"] == "down"


@pytest.mark.asyncio
async def test_ready_returns_503_when_enabled_nats_is_down(monkeypatch):
    async def nats_down():
        return {"status": "down", "error": "NATS offline"}

    monkeypatch.setattr(home, "is_nats_enabled", lambda: True)
    monkeypatch.setattr(home, "_nats_readiness", nats_down)

    response = await home.ready(HealthyDB())

    assert response.status_code == 503
    assert json.loads(response.body)["checks"]["nats"]["status"] == "down"


@pytest.mark.asyncio
async def test_split_backend_readiness_checks_both_workers(monkeypatch):
    checked_clients = []

    async def nats_ok():
        return {"status": "ok"}

    async def worker_ok(client):
        checked_clients.append(client)
        return {"status": "ok"}

    monkeypatch.setattr(home, "is_nats_enabled", lambda: True)
    monkeypatch.setattr(home, "_nats_readiness", nats_ok)
    monkeypatch.setattr(home, "_worker_readiness", worker_ok)
    monkeypatch.setattr(home.runtime_settings, "role", Role.BACKEND)

    response = await home.ready(HealthyDB())

    assert response.status_code == 200
    checks = json.loads(response.body)["checks"]
    assert checks["scheduler_worker"]["status"] == "ok"
    assert checks["node_worker"]["status"] == "ok"
    assert checked_clients == [home.scheduler_nats_client, home.node_nats_client]


@pytest.mark.asyncio
async def test_all_in_one_does_not_require_remote_workers(monkeypatch):
    async def nats_ok():
        return {"status": "ok"}

    async def unexpected_worker_check(_client):
        raise AssertionError("all-in-one readiness must not probe remote workers")

    monkeypatch.setattr(home, "is_nats_enabled", lambda: True)
    monkeypatch.setattr(home, "_nats_readiness", nats_ok)
    monkeypatch.setattr(home, "_worker_readiness", unexpected_worker_check)
    monkeypatch.setattr(home.runtime_settings, "role", Role.ALL_IN_ONE)

    response = await home.ready(HealthyDB())

    assert response.status_code == 200
    checks = json.loads(response.body)["checks"]
    assert "scheduler_worker" not in checks
    assert "node_worker" not in checks
