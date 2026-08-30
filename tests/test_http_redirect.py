from app.http_redirect import build_https_location


def test_build_https_location_adds_https_port():
    assert build_https_location("panel.example.com", "/dashboard/", 8000) == "https://panel.example.com:8000/dashboard/"


def test_build_https_location_respects_host_header_port():
    assert build_https_location("panel.example.com:8443", "/api/", 8000) == "https://panel.example.com:8443/api/"


def test_build_https_location_omits_default_https_port():
    assert build_https_location("panel.example.com", "/", 443) == "https://panel.example.com/"
