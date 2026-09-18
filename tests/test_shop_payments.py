from app.shop.payments import toman_to_rial, toman_to_usd_cents


def test_toman_conversions():
    assert toman_to_rial(1000) == 10_000
    assert toman_to_usd_cents(600_000) == 100
    assert toman_to_usd_cents(0) == 50
