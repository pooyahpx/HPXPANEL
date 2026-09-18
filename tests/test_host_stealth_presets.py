"""P4 host stealth preset catalog."""

from app.services.host_stealth_presets import get_host_stealth_preset, list_host_stealth_presets


def test_list_all_presets():
    res = list_host_stealth_presets()
    assert res.total >= 6
    stacks = {p.stack for p in res.presets}
    assert {"reality", "hysteria2", "fragment"} <= stacks


def test_filter_by_intent():
    res = list_host_stealth_presets(intent="hard")
    assert res.total >= 1
    assert all(p.intent == "hard" for p in res.presets)


def test_get_preset_has_host_patch():
    preset = get_host_stealth_preset("stealth-reality-mobile")
    assert preset is not None
    assert "fingerprint" in preset.host_patch
    assert preset.host_patch.get("fragment_settings")
