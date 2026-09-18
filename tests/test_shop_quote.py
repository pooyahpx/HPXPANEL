from app.utils.shop_quote import quote_custom_purchase, validate_custom_bounds


def test_quote_custom_purchase_extra_ip_only():
    quote = quote_custom_purchase(
        gb=20,
        days=30,
        ip_limit=3,
        price_per_gb=5000,
        price_per_day=2000,
        price_per_ip=10000,
        base_ip=1,
    )
    assert quote.data_cost == 100_000
    assert quote.days_cost == 60_000
    assert quote.extra_ip == 2
    assert quote.ip_cost == 20_000
    assert quote.amount == 180_000


def test_quote_custom_purchase_base_ip_free():
    quote = quote_custom_purchase(
        gb=10,
        days=7,
        ip_limit=1,
        price_per_gb=1000,
        price_per_day=500,
        price_per_ip=9000,
        base_ip=1,
    )
    assert quote.extra_ip == 0
    assert quote.ip_cost == 0
    assert quote.amount == 10_000 + 3_500


def test_validate_custom_bounds_rejects_out_of_range():
    try:
        validate_custom_bounds(
            gb=0,
            days=30,
            ip_limit=1,
            min_gb=1,
            max_gb=100,
            min_days=1,
            max_days=365,
            base_ip=1,
        )
        assert False, "expected ValueError"
    except ValueError:
        pass
