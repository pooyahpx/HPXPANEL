from datetime import UTC, datetime, timedelta

from app.utils.admin_create_budget import (
    calculate_create_budget_cost,
    data_limit_to_billable_gb,
    expire_to_billable_days,
    quote_from_user_payload,
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
    # unix timestamp expire
    ts = int((now + timedelta(days=10)).timestamp())
    assert expire_to_billable_days(expire=ts, now=now) == 10


def test_calculate_create_budget_cost():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    cost = calculate_create_budget_cost(
        data_limit=10 * 1024**3,
        expire=now + timedelta(days=30),
        price_per_gb=50_000,
        price_per_day=10_000,
        now=now,
    )
    assert cost.amount == 10 * 50_000 + 30 * 10_000
    assert cost.pricing_mode == "linear"


def test_custom_tier_gb_only():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    quote = calculate_create_budget_cost(
        data_limit=100 * 1024**3,
        expire=now + timedelta(days=30),
        price_per_gb=50_000,
        price_per_day=10_000,
        tiers=[{"gb": 100, "price_toman": 3_000_000}],
        now=now,
    )
    assert quote.pricing_mode == "tier"
    assert quote.data_cost == 3_000_000
    assert quote.days_cost == 30 * 10_000
    assert quote.amount == 3_000_000 + 30 * 10_000


def test_custom_tier_package():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    quote = calculate_create_budget_cost(
        data_limit=100 * 1024**3,
        expire=now + timedelta(days=30),
        price_per_gb=50_000,
        price_per_day=10_000,
        tiers=[{"gb": 100, "days": 30, "price_toman": 4_000_000}],
        now=now,
    )
    assert quote.pricing_mode == "tier"
    assert quote.amount == 4_000_000
    assert quote.days_cost == 0


def test_quote_without_expire_still_charges_gb():
    class Payload:
        status = "active"
        data_limit = 5 * 1024**3
        expire = None
        on_hold_expire_duration = None

    quote = quote_from_user_payload(Payload(), price_per_gb=20_000, price_per_day=5_000)
    assert quote.gb == 5
    assert quote.days == 0
    assert quote.amount == 100_000
