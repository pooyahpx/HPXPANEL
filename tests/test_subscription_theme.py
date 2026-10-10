from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.models.settings import DEFAULT_SUB_THEME, SUB_THEMES, Application, Platform, Subscription
from app.operation.subscription import SubscriptionOperation
from app.templates import render_template

TEMPLATE = "subscription/index.html"


def _subscription(**overrides) -> Subscription:
    return Subscription(rules=[], **overrides)


def _op() -> SubscriptionOperation:
    return SubscriptionOperation.__new__(SubscriptionOperation)


def test_subscription_theme_defaults_are_backward_compatible():
    sub = _subscription()
    assert sub.sub_theme == "terminal"
    assert sub.sub_theme_mode == "dark"
    assert sub.sub_show_install_guide is True
    assert sub.sub_show_apps is True
    assert sub.sub_show_usage_chart is True
    assert sub.sub_allow_mode_toggle is False


def test_subscription_accepts_every_known_theme():
    assert set(SUB_THEMES) == {"terminal", "aurora", "nova", "atlas", "pulse"}
    for theme in SUB_THEMES:
        assert _subscription(sub_theme=theme).sub_theme == theme


@pytest.mark.parametrize("value", ["unknown", "", None, 42, "<script>"])
def test_unknown_theme_falls_back_to_terminal(value):
    assert _subscription(sub_theme=value).sub_theme == DEFAULT_SUB_THEME


def test_unknown_mode_falls_back_to_dark():
    assert _subscription(sub_theme_mode="sepia").sub_theme_mode == "dark"
    assert _subscription(sub_theme_mode="LIGHT").sub_theme_mode == "light"


def test_theme_fields_survive_old_stored_json():
    stored = {"rules": [], "profile_title": "Old install"}
    sub = Subscription.model_validate(stored)
    assert sub.sub_theme == "terminal"
    assert "sub_theme" not in Subscription.model_validate(stored).model_fields_set


def test_default_apps_still_available_alongside_theme():
    apps = _op()._make_apps_import_urls([], {"url": "https://example.test/sub/TOKEN"}, is_hwid_enabled=False)
    assert {Platform.IOS, Platform.ANDROID, Platform.WINDOWS, Platform.MACOS} <= {app.platform for app in apps}


def _context(**overrides):
    user = SimpleNamespace(
        username="tester",
        status=SimpleNamespace(value="active"),
        used_traffic=950,
        data_limit=1000,
        lifetime_used_traffic=2000,
        expire=datetime.now(UTC) + timedelta(days=2, hours=3),
        on_hold_expire_duration=None,
        on_hold_timeout=None,
        online_at=None,
    )
    app = Application(
        name="Streisand",
        platform=Platform.IOS,
        import_url="streisand://import/{url}",
        download_links=[{"name": "App Store", "url": "https://example.test", "language": "en"}],
    )
    ctx = {
        "user": user,
        "links": ["vless://example"],
        "link_entries": [{"link": "vless://example", "remark": "", "protocol": "vless", "group_quotas": []}],
        "group_quotas": [],
        "announce": "",
        "announce_url": "",
        "support_url": "https://t.me/x",
        "is_hwid_enabled": False,
        "hwid_limit": None,
        "apps": [app],
        "profile_title": "My <VPN>",
        "sub_theme": "terminal",
        "sub_theme_mode": "dark",
        "sub_show_install_guide": True,
        "sub_show_apps": True,
        "sub_show_usage_chart": True,
        "sub_allow_mode_toggle": False,
    }
    ctx.update(overrides)
    return ctx


@pytest.mark.parametrize("theme", SUB_THEMES)
def test_template_applies_admin_theme_server_side(theme):
    html = render_template(TEMPLATE, _context(sub_theme=theme))
    assert f'<html lang="en" data-skin="{theme}">' in html


def test_template_has_no_user_facing_skin_switcher():
    html = render_template(TEMPLATE, _context())
    for needle in ("setSkin", "subSkin", "skin-seg", "data-skin-opt"):
        assert needle not in html


def test_template_unknown_theme_renders_terminal():
    html = render_template(TEMPLATE, _context(sub_theme="hacked"))
    assert 'data-skin="terminal"' in html


def test_template_mode_and_toggle_are_admin_controlled():
    dark = render_template(TEMPLATE, _context())
    assert '<body class="status-active">' in dark
    assert 'id="modeBtn"' not in dark

    light = render_template(TEMPLATE, _context(sub_theme_mode="light", sub_allow_mode_toggle=True))
    assert '<body class="status-active light">' in light
    assert 'id="modeBtn"' in light


def test_template_feature_flags_gate_sections():
    full = render_template(TEMPLATE, _context())
    assert 'id="guidePanel"' in full
    assert 'id="appsPanel"' in full
    assert 'id="usageChart"' in full

    gated = render_template(
        TEMPLATE,
        _context(sub_show_install_guide=False, sub_show_apps=False, sub_show_usage_chart=False),
    )
    assert 'id="guidePanel"' not in gated
    assert 'id="appsPanel"' not in gated
    assert 'id="usageChart"' not in gated


def test_template_warns_when_expiring_or_traffic_high_and_escapes_title():
    html = render_template(TEMPLATE, _context())
    assert 'class="alerts"' in html
    assert "My &lt;VPN&gt;" in html
    assert "My <VPN>" not in html


def test_template_keeps_chart_empty_state_fix():
    html = render_template(TEMPLATE, _context())
    assert ".chart-empty[hidden],.chart-loading[hidden]{display:none !important}" in html


def test_template_renders_for_legacy_payload_without_theme_keys():
    ctx = _context()
    for key in [k for k in ctx if k.startswith("sub_")] + ["profile_title"]:
        ctx.pop(key)
    html = render_template(TEMPLATE, ctx)
    assert 'data-skin="terminal"' in html
    assert 'id="guidePanel"' in html


@pytest.mark.parametrize("theme", SUB_THEMES)
def test_template_exposes_structural_layout_hooks(theme):
    html = render_template(TEMPLATE, _context(sub_theme=theme))
    assert f'class="shell shell-{theme}"' in html
    assert f'class="grid-top layout-{theme}"' in html
    assert 'class="grid-mid"' in html
    # connect + telemetry live in the same mid grid so skins can stack or split them
    mid = html.index('class="grid-mid"')
    assert mid < html.index('id="linksPanel"') < html.index('id="usagePanel"') < html.index('id="appsPanel"')


def test_template_mid_grid_marks_solo_when_usage_hidden():
    html = render_template(TEMPLATE, _context(sub_show_usage_chart=False))
    assert 'class="grid-mid solo"' in html


@pytest.mark.parametrize("theme", ["aurora", "nova", "atlas", "pulse"])
def test_template_skins_define_distinct_top_layouts(theme):
    html = render_template(TEMPLATE, _context(sub_theme=theme))
    assert f'[data-skin="{theme}"] .grid-top' in html
