"""Assert critical i18n namespaces exist in Russian and Chinese locale files."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

LOCALES_DIR = Path(__file__).resolve().parents[1] / "dashboard" / "public" / "statics" / "locales"

REQUIRED_TOP_LEVEL = ("openvpn", "hpxPulse", "observability", "audit")


def _load(lang: str) -> dict:
    path = LOCALES_DIR / f"{lang}.json"
    assert path.is_file(), f"Missing locale file: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("lang", ["ru", "zh"])
def test_critical_namespaces_present(lang: str) -> None:
    data = _load(lang)
    for key in REQUIRED_TOP_LEVEL:
        assert key in data, f"{lang}.json missing top-level key: {key}"
    settings = data.get("settings")
    assert isinstance(settings, dict), f"{lang}.json missing settings object"
    assert "backup" in settings, f"{lang}.json missing settings.backup"
