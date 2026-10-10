from app.models.settings import Platform
from app.operation.subscription import SubscriptionOperation


def _op() -> SubscriptionOperation:
    return SubscriptionOperation.__new__(SubscriptionOperation)


def test_default_apps_fallback_when_none_configured():
    apps = _op()._make_apps_import_urls([], {"url": "https://example.test/sub/TOKEN"}, is_hwid_enabled=False)

    platforms = {app.platform for app in apps}
    assert {Platform.IOS, Platform.ANDROID, Platform.WINDOWS, Platform.MACOS} <= platforms
    assert all(app.download_links for app in apps)

    streisand = next(app for app in apps if app.name == "Streisand")
    assert streisand.import_url == "streisand://import/https://example.test/sub/TOKEN"


def test_default_apps_visible_with_hwid_enabled():
    apps = _op()._make_apps_import_urls([], {"url": "https://example.test/sub/TOKEN"}, is_hwid_enabled=True)
    assert apps
