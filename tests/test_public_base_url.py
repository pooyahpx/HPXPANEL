"""Public panel URL normalization for Pulse/Abroad join commands."""

from app.utils.helpers import normalize_public_base_url, public_base_url_from_request


def test_normalize_strips_https_443():
    assert normalize_public_base_url("https://pnl.example.com:443/") == "https://pnl.example.com"


def test_normalize_keeps_panel_port_8000_on_https():
    assert normalize_public_base_url("https://pnl.duolingoo.ir:8000") == "https://pnl.duolingoo.ir:8000"


def test_normalize_keeps_nondefault_port():
    assert normalize_public_base_url("https://pnl.example.com:8443") == "https://pnl.example.com:8443"


class _Headers(dict):
    def get(self, key, default=None):
        return super().get(key.lower(), default)


class _Url:
    def __init__(self, scheme: str, netloc: str):
        self.scheme = scheme
        self.netloc = netloc


class _Request:
    def __init__(self, headers: dict, scheme: str = "https", netloc: str = "ignored:8000"):
        # Starlette headers are case-insensitive; our helper lowercases keys via .get on dict —
        # normalize keys to lower for the stub.
        self.headers = _Headers({k.lower(): v for k, v in headers.items()})
        self.url = _Url(scheme, netloc)
        self.base_url = f"{scheme}://{netloc}/"


def test_request_uses_host_port_8000_when_browsing_panel_directly():
    req = _Request(
        {
            "x-forwarded-proto": "https",
            "host": "pnl.fastapex11.shop:8000",
        }
    )
    assert public_base_url_from_request(req) == "https://pnl.fastapex11.shop:8000"


def test_request_keeps_forwarded_host_when_proxy_on_443():
    req = _Request(
        {
            "x-forwarded-proto": "https",
            "x-forwarded-host": "pnl.duolingoo.ir",
            "host": "pnl.duolingoo.ir:8000",
        }
    )
    # Reverse-proxy publishes the public host without :8000.
    assert public_base_url_from_request(req) == "https://pnl.duolingoo.ir"


def test_request_appends_forwarded_port_8000():
    req = _Request(
        {
            "x-forwarded-proto": "https",
            "x-forwarded-host": "pnl.fastapex11.shop",
            "x-forwarded-port": "8000",
            "host": "pnl.fastapex11.shop",
        }
    )
    assert public_base_url_from_request(req) == "https://pnl.fastapex11.shop:8000"
