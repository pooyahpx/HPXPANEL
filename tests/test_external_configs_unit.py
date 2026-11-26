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
    proxy = SimpleNamespace(vless=SimpleNamespace(id="11111111-1111-1111-1111-111111111111"))
    active_with_quota = SimpleNamespace(status="active", data_limit=10_000, used_traffic=1_000, proxy_settings=proxy)
    exhausted = SimpleNamespace(status="active", data_limit=10_000, used_traffic=10_000, proxy_settings=proxy)
    limited_status = SimpleNamespace(status="limited", data_limit=None, used_traffic=0, proxy_settings=proxy)

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
                personalize=True,
            )
        ]
    )
    exhausted_but_active = SimpleNamespace(
        status="active",
        data_limit=10,
        used_traffic=10,
        proxy_settings=SimpleNamespace(vless=SimpleNamespace(id="11111111-1111-1111-1111-111111111111")),
    )
    disabled = SimpleNamespace(status="disabled", data_limit=None, used_traffic=0)
    assert len(collect_external_config_links(settings, user=exhausted_but_active)) == 1
    assert collect_external_config_links(settings, user=disabled) == []


def test_shared_uuid_mode_always_respects_quota(monkeypatch):
    monkeypatch.setattr(
        "app.subscription.external_configs.subscription_env_settings",
        SimpleNamespace(external_config=""),
    )
    settings = SimpleNamespace(
        external_configs=[
            ExternalConfig(
                name="Shared",
                link="vless://shared@host:1?encryption=none#s",
                enabled=True,
                respect_user_quota=False,
                personalize=False,
            )
        ]
    )
    exhausted = SimpleNamespace(status="active", data_limit=10, used_traffic=10)
    assert collect_external_config_links(settings, user=exhausted) == []


def test_personalize_rewrites_vless_uuid(monkeypatch):
    monkeypatch.setattr(
        "app.subscription.external_configs.subscription_env_settings",
        SimpleNamespace(external_config=""),
    )
    local_uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    settings = SimpleNamespace(
        external_configs=[
            ExternalConfig(
                name="Mother",
                link="vless://mother-uuid@mooz.example:2082?encryption=none&security=reality#old",
                enabled=True,
                personalize=True,
            )
        ]
    )
    user = SimpleNamespace(
        status="active",
        data_limit=None,
        used_traffic=0,
        proxy_settings=SimpleNamespace(vless=SimpleNamespace(id=local_uuid)),
    )
    links = collect_external_config_links(settings, user=user)
    assert len(links) == 1
    assert links[0].startswith(f"vless://{local_uuid}@mooz.example:2082")
    assert "mother-uuid" not in links[0]
    assert links[0].endswith("#Mother")


def test_personalize_false_keeps_shared_uuid(monkeypatch):
    monkeypatch.setattr(
        "app.subscription.external_configs.subscription_env_settings",
        SimpleNamespace(external_config=""),
    )
    settings = SimpleNamespace(
        external_configs=[
            ExternalConfig(
                name="Shared",
                link="vless://shared-uuid@host:443?encryption=none#x",
                enabled=True,
                personalize=False,
            )
        ]
    )
    user = SimpleNamespace(
        status="active",
        data_limit=None,
        used_traffic=0,
        proxy_settings=SimpleNamespace(vless=SimpleNamespace(id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")),
    )
    links = collect_external_config_links(settings, user=user)
    assert links == ["vless://shared-uuid@host:443?encryption=none#Shared"]
