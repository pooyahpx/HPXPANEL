from types import SimpleNamespace

from app.models.settings import ExternalConfig
from app.subscription.external_configs import (
    collect_external_config_links,
    normalize_external_link,
    user_may_receive_external_configs,
)


def test_normalize_external_link_overrides_remark():
    link = "vless://uuid@host:443?security=reality#old"
    assert normalize_external_link(link, "Mother") == "vless://uuid@host:443?security=reality#Mother"


def test_collect_external_configs_skips_disabled_and_dedupes(monkeypatch):
    monkeypatch.setattr(
        "app.subscription.external_configs.subscription_env_settings",
        SimpleNamespace(external_config="vless://env@host:1?encryption=none#env"),
    )
    settings = SimpleNamespace(
        external_configs=[
            ExternalConfig(name="A", link="vless://a@host:1?encryption=none#a", enabled=True),
            ExternalConfig(name="B", link="vless://a@host:1?encryption=none#other", enabled=True),
            ExternalConfig(name="Off", link="vless://off@host:1?encryption=none#off", enabled=False),
        ]
    )
    links = collect_external_config_links(settings)
    assert len(links) == 2
    assert links[0].endswith("#A")
    assert any(link.startswith("vless://env@") for link in links)


def test_external_config_rejects_garbage():
    try:
        ExternalConfig(name="x", link="not-a-link")
        raised = False
    except Exception:
        raised = True
    assert raised


def test_quota_gate_hides_mother_for_exhausted_user(monkeypatch):
    monkeypatch.setattr(
        "app.subscription.external_configs.subscription_env_settings",
        SimpleNamespace(external_config=""),
    )
    settings = SimpleNamespace(
        external_configs=[
            ExternalConfig(
                name="Mother",
                link="vless://m@host:1?encryption=none#m",
                enabled=True,
                respect_user_quota=True,
            )
        ]
    )
    active_with_quota = SimpleNamespace(status="active", data_limit=10_000, used_traffic=1_000)
    exhausted = SimpleNamespace(status="active", data_limit=10_000, used_traffic=10_000)
    limited_status = SimpleNamespace(status="limited", data_limit=None, used_traffic=0)

    assert user_may_receive_external_configs(active_with_quota) is True
    assert user_may_receive_external_configs(exhausted) is False
    assert user_may_receive_external_configs(limited_status) is False

    assert len(collect_external_config_links(settings, user=active_with_quota)) == 1
    assert collect_external_config_links(settings, user=exhausted) == []


def test_respect_user_quota_false_still_requires_active(monkeypatch):
    monkeypatch.setattr(
        "app.subscription.external_configs.subscription_env_settings",
        SimpleNamespace(external_config=""),
    )
    settings = SimpleNamespace(
        external_configs=[
            ExternalConfig(
                name="Open",
                link="vless://o@host:1?encryption=none#o",
                enabled=True,
                respect_user_quota=False,
            )
        ]
    )
    exhausted_but_active = SimpleNamespace(status="active", data_limit=10, used_traffic=10)
    disabled = SimpleNamespace(status="disabled", data_limit=None, used_traffic=0)
    assert len(collect_external_config_links(settings, user=exhausted_but_active)) == 1
    assert collect_external_config_links(settings, user=disabled) == []
