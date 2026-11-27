"""Unit tests for shared-UUID mother traffic metering."""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.settings import ExternalConfig
from app.services import mother_usage_meter as meter


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _DB:
    def __init__(self, results: list):
        self._results = list(results)
        self.commits = 0
        self.execute_calls = 0

    async def execute(self, _stmt):
        self.execute_calls += 1
        if not self._results:
            return _Result([])
        return self._results.pop(0)

    async def commit(self):
        self.commits += 1


def test_cfg_fields_reads_respect_quota():
    cfg = ExternalConfig(
        name="M",
        link="vless://u@host.example:443#x",
        enabled=True,
        personalize=False,
        respect_user_quota=True,
    )
    enabled, personalize, respect, link = meter._cfg_fields(cfg)
    assert enabled is True
    assert personalize is False
    assert respect is True
    assert link


@pytest.mark.asyncio
async def test_mother_node_ids_skips_personalized_and_no_quota():
    db = _DB([_Result([(1, "shared.example"), (2, "bound.example")])])
    subscription = SimpleNamespace(
        external_configs=[
            ExternalConfig(
                name="Shared",
                link="vless://u@shared.example:2082#s",
                enabled=True,
                personalize=False,
                respect_user_quota=True,
            ),
            ExternalConfig(
                name="Bound",
                link="vless://u@bound.example:2082#b",
                enabled=True,
                personalize=True,
                respect_user_quota=True,
            ),
            ExternalConfig(
                name="Unlimited",
                link="vless://u@shared.example:2082#u",
                enabled=True,
                personalize=False,
                respect_user_quota=False,
            ),
        ]
    )
    matched = await meter.mother_node_ids_for_shared_configs(db, subscription)
    assert matched == {1}


@pytest.mark.asyncio
async def test_eligible_mother_user_ids_prefers_recent_online():
    now = dt.now(UTC)
    rows = _Result(
        [
            (1, "active", 1000, 0, now - timedelta(minutes=1)),  # recent
            (2, "active", 1000, 0, now - timedelta(hours=2)),  # stale
            (3, "active", 1000, 1000, now),  # exhausted
            (4, "expired", 1000, 0, now),
            (5, "on_hold", None, 10, None),  # unlimited, not recent
        ]
    )
    db = _DB([rows])
    ids = await meter.eligible_mother_user_ids(db)
    assert ids == [1]


@pytest.mark.asyncio
async def test_eligible_falls_back_when_nobody_recent():
    now = dt.now(UTC)
    rows = _Result(
        [
            (1, "active", 1000, 0, now - timedelta(hours=2)),
            (2, "active", 500, 100, None),
            (3, "disabled", 1000, 0, None),
        ]
    )
    db = _DB([rows])
    ids = await meter.eligible_mother_user_ids(db)
    assert ids == [1, 2]


@pytest.mark.asyncio
async def test_distribute_bytes_to_users_splits_and_updates_admins():
    db = _DB([_Result([(10, 1), (11, 1), (12, None)])])
    applied = await meter.distribute_bytes_to_users(db, user_ids=[10, 11, 12], total_bytes=100)
    assert applied == 100
    assert db.commits == 1
    # 3 user updates + 1 admin update
    assert db.execute_calls == 1 + 3 + 1


@pytest.mark.asyncio
async def test_touch_mother_soft_online_updates_when_shared_enabled():
    class _UpdateResult:
        rowcount = 1

    class _TouchDB(_DB):
        async def execute(self, _stmt):
            self.execute_calls += 1
            return _UpdateResult()

    db = _TouchDB([])
    subscription = SimpleNamespace(
        external_configs=[
            ExternalConfig(
                name="Shared",
                link="vless://u@foreign.example:443#x",
                enabled=True,
                personalize=False,
            )
        ]
    )
    ok = await meter.touch_mother_soft_online(db, user_id=7, subscription=subscription)
    assert ok is True
    assert db.commits == 1


@pytest.mark.asyncio
async def test_touch_mother_soft_online_skips_when_only_bound():
    db = _DB([])
    subscription = SimpleNamespace(
        external_configs=[
            ExternalConfig(
                name="Bound",
                link="vless://u@host.example:443#x",
                enabled=True,
                personalize=True,
            )
        ]
    )
    ok = await meter.touch_mother_soft_online(db, user_id=7, subscription=subscription)
    assert ok is False
    assert db.commits == 0


@pytest.mark.asyncio
async def test_apply_orphaned_mother_traffic_distributes_pool(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        meter,
        "mother_node_ids_for_shared_configs",
        AsyncMock(return_value={7, 8}),
    )
    monkeypatch.setattr(meter, "eligible_mother_user_ids", AsyncMock(return_value=[1, 2]))
    distribute = AsyncMock(return_value=900)
    monkeypatch.setattr(meter, "distribute_bytes_to_users", distribute)

    db = _DB([])
    applied = await meter.apply_orphaned_mother_traffic(
        db,
        subscription=SimpleNamespace(external_configs=[]),
        orphaned_by_node={7: 400, 8: 500, 9: 999},  # node 9 not mother
    )
    assert applied == 900
    distribute.assert_awaited_once()
    assert distribute.await_args.kwargs["total_bytes"] == 900
    assert distribute.await_args.kwargs["user_ids"] == [1, 2]


@pytest.mark.asyncio
async def test_apply_orphaned_skips_when_no_mother_nodes(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(meter, "mother_node_ids_for_shared_configs", AsyncMock(return_value=set()))
    distribute = AsyncMock()
    monkeypatch.setattr(meter, "distribute_bytes_to_users", distribute)

    applied = await meter.apply_orphaned_mother_traffic(
        _DB([]),
        subscription=None,
        orphaned_by_node={1: 100},
    )
    assert applied == 0
    distribute.assert_not_awaited()
