from types import SimpleNamespace

from app.models.settings import ExternalConfig
from app.subscription.external_configs import collect_external_config_links, normalize_external_link


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
