from types import SimpleNamespace

import pytest
from nats.js.errors import KeyNotFoundError, KeyWrongLastSequenceError

from app import scheduler_lock
from app.scheduler_lock import SchedulerLockManager
from config import SchedulerLockSettings


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

    async def delete(self, key, last=None):
        if key not in self.data or self.data[key][1] != last:
            raise KeyWrongLastSequenceError()
        del self.data[key]
        return True


def manager(kv, now, owner):
    result = SchedulerLockManager(clock=lambda: now[0], owner_id=owner)
    result.set_kv_for_testing(kv)
    return result


@pytest.mark.asyncio
async def test_scheduler_lock_acquisition(monkeypatch):
    monkeypatch.setattr(scheduler_lock, "is_nats_enabled", lambda: True)
    lease = await manager(FakeKV(), [100.0], "one").acquire("job")

    assert lease is not None
    assert lease.owner == "one"
    assert lease.revision == 1


@pytest.mark.asyncio
async def test_scheduler_lock_contention(monkeypatch):
    monkeypatch.setattr(scheduler_lock, "is_nats_enabled", lambda: True)
    kv = FakeKV()
    now = [100.0]
    first = manager(kv, now, "one")
    second = manager(kv, now, "two")

    assert await first.acquire("job") is not None
    assert await second.acquire("job") is None


@pytest.mark.asyncio
async def test_scheduler_lock_recovers_expired_lease(monkeypatch):
    monkeypatch.setattr(scheduler_lock, "is_nats_enabled", lambda: True)
    kv = FakeKV()
    now = [100.0]
    first = manager(kv, now, "one")
    second = manager(kv, now, "two")

    assert await first.acquire("job") is not None
    now[0] = 1000.0
    recovered = await second.acquire("job")

    assert recovered is not None
    assert recovered.owner == "two"


@pytest.mark.asyncio
async def test_scheduler_lock_no_nats_fallback_runs_job(monkeypatch):
    monkeypatch.setattr(scheduler_lock, "is_nats_enabled", lambda: False)
    lock_manager = SchedulerLockManager(owner_id="local")
    called = []

    async def job(value):
        called.append(value)
        return value

    result = await lock_manager.run_locked("job", job, 42)

    assert result == 42
    assert called == [42]


def test_scheduler_lock_configuration_renews_before_expiry():
    with pytest.raises(ValueError, match="plus SCHEDULER_LOCK_OPERATION_TIMEOUT"):
        SchedulerLockSettings(
            SCHEDULER_LOCK_LEASE_SECONDS=30,
            SCHEDULER_LOCK_RENEW_INTERVAL=25,
            SCHEDULER_LOCK_OPERATION_TIMEOUT=5,
        )
