from datetime import UTC, datetime, timedelta

from app.utils.admin_create_budget import (
    calculate_create_budget_cost,
    data_limit_to_billable_gb,
    expire_to_billable_days,
)


def test_data_limit_to_billable_gb():
    assert data_limit_to_billable_gb(None) == 0
    assert data_limit_to_billable_gb(0) == 0
    assert data_limit_to_billable_gb(1024**3) == 1
    assert data_limit_to_billable_gb(1024**3 + 1) == 2


def test_expire_to_billable_days():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    assert expire_to_billable_days(expire=None, now=now) == 0
    assert expire_to_billable_days(expire=now + timedelta(days=30), now=now) == 30
    assert expire_to_billable_days(on_hold_expire_duration=86_400 * 7, now=now) == 7


def test_calculate_create_budget_cost():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    cost = calculate_create_budget_cost(
        data_limit=10 * 1024**3,
        expire=now + timedelta(days=30),
        price_per_gb=50_000,
        price_per_day=10_000,
        now=now,
    )
    assert cost == 10 * 50_000 + 30 * 10_000
