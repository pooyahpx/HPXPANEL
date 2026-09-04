from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from nats.js.errors import KeyNotFoundError, KeyWrongLastSequenceError
from starlette.requests import Request as StarletteRequest

from app.rate_limit import InMemoryRateLimitBackend, NatsRateLimitBackend, RateLimiter, RateLimitPolicy
from config import rate_limit_settings


class FakeKV:
    def __init__(self):
        self.data = {}
        self.revision = 0

    async def get(self, key):
        if key not in self.data:
            raise KeyNotFoundError()
        value, revision = self.data[key]
        return SimpleNamespace(value=value, revision=revision)

    async def create(self, key, value):
        if key in self.data:
            raise KeyWrongLastSequenceError()
        self.revision += 1
        self.data[key] = (value, self.revision)
        return self.revision

    async def update(self, key, value, last=None):
        if key not in self.data or self.data[key][1] != last:
            raise KeyWrongLastSequenceError()
        self.revision += 1
        self.data[key] = (value, self.revision)
        return self.revision


@pytest.mark.asyncio
async def test_in_memory_rate_limit_and_window_reset():
    now = [100.0]
    backend = InMemoryRateLimitBackend(max_keys=100, clock=lambda: now[0])
    policy = RateLimitPolicy("login", 2, 10)

    assert (await backend.check("key", policy)).allowed
    assert (await backend.check("key", policy)).allowed
    denied = await backend.check("key", policy)
    assert not denied.allowed
    assert denied.retry_after == 10

    now[0] = 111.0
    assert (await backend.check("key", policy)).allowed


@pytest.mark.asyncio
async def test_in_memory_backend_bounds_key_count():
    backend = InMemoryRateLimitBackend(max_keys=2)
    policy = RateLimitPolicy("subscription", 10, 60)

    await backend.check("one", policy)
    await backend.check("two", policy)
    await backend.check("three", policy)

    assert len(backend._entries) == 2


@pytest.mark.asyncio
async def test_nats_backend_uses_shared_atomic_counter():
    now = [1000.0]
    kv = FakeKV()
    first = NatsRateLimitBackend(clock=lambda: now[0])
    second = NatsRateLimitBackend(clock=lambda: now[0])
    first._kv = kv
    second._kv = kv
    policy = RateLimitPolicy("claim", 2, 30)

    assert (await first.check("same", policy)).allowed
    assert (await second.check("same", policy)).allowed
    denied = await first.check("same", policy)
    assert not denied.allowed
    assert denied.retry_after == 30


def test_rate_limiter_api_returns_429_with_retry_after(monkeypatch):
    monkeypatch.setattr(rate_limit_settings, "enabled", True)
    limiter = RateLimiter()
    limiter.set_backend_for_testing(InMemoryRateLimitBackend(max_keys=100))
    app = FastAPI()

    @app.get("/limited")
    async def limited(request: Request):
        await limiter.enforce(request, "test", 1, 60, identity="account")
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/limited").status_code == 200
    response = client.get("/limited")
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"


@pytest.mark.asyncio
async def test_distributed_backend_failure_fails_closed(monkeypatch):
    monkeypatch.setattr(rate_limit_settings, "enabled", True)
    backend = NatsRateLimitBackend()

    async def unavailable():
        raise RuntimeError("NATS offline")

    monkeypatch.setattr(backend, "_get_kv", unavailable)
    limiter = RateLimiter()
    limiter.set_backend_for_testing(backend)
    request = StarletteRequest({"type": "http", "client": ("127.0.0.1", 1234), "headers": []})

    with pytest.raises(HTTPException) as exc_info:
        await limiter.enforce(request, "login", 1, 60)

    assert exc_info.value.status_code == 503
    assert exc_info.value.headers["Retry-After"] == str(rate_limit_settings.unavailable_retry_after)


@pytest.mark.asyncio
async def test_dual_login_policy_blocks_identity_rotation(monkeypatch):
    monkeypatch.setattr(rate_limit_settings, "enabled", True)
    backend = InMemoryRateLimitBackend(max_keys=100)
    limiter = RateLimiter()
    limiter.set_backend_for_testing(backend)
    request = StarletteRequest({"type": "http", "client": ("192.0.2.1", 1234), "headers": []})

    await limiter.enforce_client_and_identity(request, "login", 2, 60, identity="first-user")
    await limiter.enforce_client_and_identity(request, "login", 2, 60, identity="second-user")
    with pytest.raises(HTTPException) as exc_info:
        await limiter.enforce_client_and_identity(request, "login", 2, 60, identity="third-user")

    assert exc_info.value.status_code == 429
    assert len(backend._entries) == 3
    assert all("user" not in key for key in backend._entries)


@pytest.mark.asyncio
async def test_dual_login_policy_does_not_halve_identity_limit(monkeypatch):
    monkeypatch.setattr(rate_limit_settings, "enabled", True)
    backend = InMemoryRateLimitBackend(max_keys=100)
    limiter = RateLimiter()
    limiter.set_backend_for_testing(backend)
    request = StarletteRequest({"type": "http", "client": ("192.0.2.2", 1234), "headers": []})

    await limiter.enforce_client_and_identity(request, "login", 2, 60, identity="same-user")
    await limiter.enforce_client_and_identity(request, "login", 2, 60, identity="same-user")
    with pytest.raises(HTTPException) as exc_info:
        await limiter.enforce_client_and_identity(request, "login", 2, 60, identity="same-user")

    assert exc_info.value.status_code == 429
    assert len(backend._entries) == 2
