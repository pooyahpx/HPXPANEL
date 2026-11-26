"""Unit tests for mother-config consumption aggregation."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.settings import ExternalConfig
from app.services.mother_config_usage import compute_mother_config_usage, mother_link_host


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _DB:
    """Minimal async DB stub that returns queued execute results in order."""

    def __init__(self, results: list):
        self._results = list(results)

    async def execute(self, _stmt):
        if not self._results:
            return _Result([])
        return self._results.pop(0)


def test_mother_link_host_parses_vless():
    assert mother_link_host("vless://u@mooz.example:2082?encryption=none#x") == "mooz.example"
    assert mother_link_host("not-a-link") is None


@pytest.mark.asyncio
async def test_compute_mother_config_usage_aggregates_eligibility():
    # users: id, status, data_limit, used_traffic
    user_rows = _Result(
        [
            (1, "active", 1000, 200),  # eligible
            (2, "active", 1000, 1000),  # exhausted
            (3, "on_hold", None, 50),  # unlimited eligible
            (4, "expired", 500, 10),
            (5, "disabled", 0, 0),
        ]
    )
    # nodes: id, address — mother host matches node 10
    node_rows = _Result([(10, "mooz.example"), (11, "other.example")])
    # recent usage on mother node: only user 1 (eligible) — user 99 ignored
    usage_rows = _Result([(10, 1), (10, 99)])

    db = _DB([user_rows, node_rows, usage_rows])

    subscription = SimpleNamespace(
        external_configs=[
            ExternalConfig(
                name="Mother A",
                link="vless://m@mooz.example:2082?encryption=none#m",
                enabled=True,
                respect_user_quota=True,
                personalize=True,
            ),
            ExternalConfig(
                name="Mother B",
                link="vless://m@other.example:443?encryption=none#m",
                enabled=True,
                respect_user_quota=False,
                personalize=True,
            ),
            ExternalConfig(
                name="Off",
                link="vless://m@mooz.example:2082?encryption=none#off",
                enabled=False,
                respect_user_quota=True,
            ),
        ]
    )

    out = await compute_mother_config_usage(db, subscription)

    assert out.total_users == 5
    assert out.active_users == 2
    assert out.on_hold_users == 1
    assert out.eligible_for_quota_gated == 2
    assert out.exhausted_volume == 1
    assert out.unlimited_users == 1
    assert out.online_users == 1  # only user 1 on matched mother nodes + eligible
    assert out.matched_node_ids == [10, 11]
    assert out.enabled_configs == 2
    assert out.total_configs == 3

    a, b, off = out.configs
    assert a.name == "Mother A"
    assert a.host == "mooz.example"
    assert a.matched_node_ids == [10]
    assert a.eligible_users == 2
    assert a.online_users == 1
    assert a.gated_by_quota == 1

    assert b.name == "Mother B"
    assert b.host == "other.example"
    assert b.matched_node_ids == [11]
    assert b.eligible_users == 3  # status-only when respect=false + personalize
    assert b.online_users == 0  # no usage rows for node 11
    assert b.gated_by_quota == 0

    assert off.enabled is False
    assert off.online_users == 0


@pytest.mark.asyncio
async def test_shared_uuid_reports_zero_mother_online():
    user_rows = _Result([(1, "active", None, 0)])
    node_rows = _Result([(10, "mooz.example")])
    usage_rows = _Result([(10, 1)])  # would look online, but personalize=false
    db = _DB([user_rows, node_rows, usage_rows])
    subscription = SimpleNamespace(
        external_configs=[
            ExternalConfig(
                name="Shared",
                link="vless://shared@mooz.example:2082?encryption=none#s",
                enabled=True,
                personalize=False,
            )
        ]
    )
    out = await compute_mother_config_usage(db, subscription)
    assert out.online_users == 0
    assert out.configs[0].online_users == 0


@pytest.mark.asyncio
async def test_general_online_without_mother_node_match_is_zero():
    """Panel-online users must NOT inflate mother online when host ≠ any Node.address."""
    user_rows = _Result([(1, "active", None, 0)])
    node_rows = _Result([(10, "local-node.example")])
    # no mother-matched nodes → no usage query
    db = _DB([user_rows, node_rows])
    subscription = SimpleNamespace(
        external_configs=[
            ExternalConfig(
                name="Foreign",
                link="vless://x@foreign-mother.shop:2082?encryption=none#f",
                enabled=True,
                personalize=True,
            )
        ]
    )
    out = await compute_mother_config_usage(db, subscription)
    assert out.matched_node_ids == []
    assert out.online_users == 0
    assert out.configs[0].online_users == 0
    assert out.configs[0].host == "foreign-mother.shop"


@pytest.mark.asyncio
async def test_compute_mother_config_usage_empty_subscription():
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[_Result([]), _Result([])])
    out = await compute_mother_config_usage(db, None)
    assert out.total_users == 0
    assert out.configs == []
    assert out.enabled_configs == 0
    assert out.usage_pct == 0.0
    assert out.online_users == 0
