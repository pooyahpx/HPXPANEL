from app.utils.shop_quote import apply_discount_amount


def test_percent_discount():
    q = apply_discount_amount(original_toman=100_000, percent_off=20, code="OFF20")
    assert q.original == 100_000
    assert q.discount == 20_000
    assert q.final == 80_000
    assert q.code == "OFF20"


def test_amount_discount_capped():
    q = apply_discount_amount(original_toman=50_000, amount_off_toman=80_000, code="BIG")
    assert q.discount == 50_000
    assert q.final == 0


def test_percent_wins_over_amount():
    q = apply_discount_amount(original_toman=10_000, percent_off=10, amount_off_toman=9_000, code="X")
    assert q.discount == 1_000
    assert q.final == 9_000
