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

def test_default_apps_cover_every_desktop_and_mobile_platform():
    from app.subscription.default_apps import build_default_applications

    apps = build_default_applications()
    by_platform: dict[Platform, set[str]] = {}
    for app in apps:
        by_platform.setdefault(app.platform, set()).add(app.name)

    assert {"Streisand", "Shadowrocket", "V2Box"} <= by_platform[Platform.IOS]
    assert {"v2rayNG", "Hiddify"} <= by_platform[Platform.ANDROID]
    assert {"v2rayN", "Hiddify"} <= by_platform[Platform.WINDOWS]
    assert {"V2Box", "Hiddify"} <= by_platform[Platform.MACOS]
    assert "Hiddify" in by_platform[Platform.LINUX]


def test_default_apps_have_real_links_and_valid_imports():
    from app.subscription.default_apps import build_default_applications

    apps = build_default_applications()
    for app in apps:
        assert app.download_links, app.name
        for link in app.download_links:
            assert link.url.startswith("https://"), (app.name, link.url)
            assert "example" not in link.url
        if app.import_url:
            assert "{url}" in app.import_url, app.name
        assert app.description.get("en"), app.name
        assert app.description.get("fa"), app.name


def test_default_apps_one_recommended_per_platform():
    from app.subscription.default_apps import build_default_applications

    seen: dict[Platform, list[str]] = {}
    for app in build_default_applications():
        if app.recommended:
            seen.setdefault(app.platform, []).append(app.name)
    assert all(len(names) == 1 for names in seen.values()), seen
    assert {Platform.IOS, Platform.ANDROID, Platform.WINDOWS, Platform.MACOS, Platform.LINUX} <= set(seen)
