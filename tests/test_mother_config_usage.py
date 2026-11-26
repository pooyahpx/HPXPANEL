"""Unit tests for mother-config consumption aggregation."""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.settings import ExternalConfig
from app.services.mother_config_usage import compute_mother_config_usage


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


@pytest.mark.asyncio
async def test_compute_mother_config_usage_aggregates_eligibility():
    now = dt.now(UTC)
    rows = [
        ("active", 1000, 200, now),  # eligible limited + online
        ("active", 1000, 1000, None),  # exhausted
        ("on_hold", None, 50, now - timedelta(minutes=10)),  # unlimited eligible, offline
        ("expired", 500, 10, None),  # status gated
        ("disabled", 0, 0, None),  # status gated
    ]
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_Result(rows))

    subscription = SimpleNamespace(
        external_configs=[
            ExternalConfig(name="Mother A", link="vless://mother-a-example", enabled=True, respect_user_quota=True),
            ExternalConfig(
                name="Mother B",
                link="vless://mother-b-example",
                enabled=True,
                respect_user_quota=False,
                personalize=True,
            ),
            ExternalConfig(name="Off", link="vless://mother-c-example", enabled=False, respect_user_quota=True),
        ]
    )

    out = await compute_mother_config_usage(db, subscription)

    assert out.total_users == 5
    assert out.active_users == 2
    assert out.on_hold_users == 1
    assert out.expired_users == 1
    assert out.disabled_users == 1
    assert out.eligible_for_quota_gated == 2  # limited remaining + unlimited
    assert out.exhausted_volume == 1
    assert out.unlimited_users == 1
    assert out.online_users == 1
    assert out.used_traffic_bytes == 200 + 1000 + 50 + 10 + 0
    assert out.data_limit_bytes == 1000 + 1000 + 500
    assert out.remaining_bytes == 800  # only limited eligible remaining
    assert out.usage_pct == 20.0  # 200/1000
    assert out.enabled_configs == 2
    assert out.total_configs == 3
    assert out.personalized_configs == 2

    a, b, off = out.configs
    assert a.name == "Mother A"
    assert a.eligible_users == 2
    assert a.online_users == 1
    assert a.gated_by_quota == 1
    assert a.gated_by_status == 2

    assert b.name == "Mother B"
    assert b.eligible_users == 3  # active + on_hold, ignore quota
    assert b.gated_by_quota == 0
    assert b.gated_by_status == 2

    assert off.enabled is False
    assert off.eligible_users == 0


@pytest.mark.asyncio
async def test_compute_mother_config_usage_empty_subscription():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_Result([]))
    out = await compute_mother_config_usage(db, None)
    assert out.total_users == 0
    assert out.configs == []
    assert out.enabled_configs == 0
    assert out.usage_pct == 0.0
    assert out.online_users == 0
