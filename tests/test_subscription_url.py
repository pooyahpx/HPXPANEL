import pytest

from app.utils.helpers import resolve_subscription_url_prefix, url_origin


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://pnl.duolingoo.ir/api/telegram/webhook", "https://pnl.duolingoo.ir"),
        ("https://pnl.duolingoo.ir/", "https://pnl.duolingoo.ir"),
        ("http://localhost:8000", "http://localhost:8000"),
        ("", None),
        (None, None),
        ("/sub/token", None),
    ],
)
def test_url_origin(url, expected):
    assert url_origin(url) == expected


@pytest.mark.parametrize(
    ("url_prefix", "panel_base", "expected"),
    [
        ("", "https://pnl.duolingoo.ir", "https://pnl.duolingoo.ir"),
        ("https://pnl.duolingoo.ir", None, "https://pnl.duolingoo.ir"),
        ("sub.example.com", None, "https://sub.example.com"),
        ("custom", "https://pnl.duolingoo.ir", "https://pnl.duolingoo.ir/custom"),
        ("", None, ""),
    ],
)
def test_resolve_subscription_url_prefix(url_prefix, panel_base, expected):
    assert resolve_subscription_url_prefix(url_prefix, panel_base) == expected
