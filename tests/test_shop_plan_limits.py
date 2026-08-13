import pytest

from app.telegram.utils.shop_helpers import parse_optional_limit


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("-", None),
        ("", None),
        ("نامحدود", None),
        ("3", 3),
        ("0", 0),
    ],
)
def test_parse_optional_limit(raw, expected):
    assert parse_optional_limit(raw) == expected


def test_parse_optional_limit_rejects_negative():
    with pytest.raises(ValueError):
        parse_optional_limit("-2")
