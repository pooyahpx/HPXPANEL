from pathlib import Path

import pytest

from copilot_env_store import (
    apply_copilot_env_file_to_os_environ,
    mask_secret,
    read_env_file,
    update_copilot_env,
    write_env_file,
)


def test_mask_secret():
    assert mask_secret("") == ""
    assert mask_secret("short") == "••••••••"
    assert mask_secret("gsk_abcdefghijklmnop") == "gsk_…mnop"


def test_write_and_read_env_file(tmp_path: Path):
    env_file = tmp_path / "copilot.env"
    write_env_file(env_file, {"COPILOT_PROVIDER": "groq", "OPENAI_API_KEY": "gsk_test_key"})
    values = read_env_file(env_file)
    assert values["COPILOT_PROVIDER"] == "groq"
    assert values["OPENAI_API_KEY"] == "gsk_test_key"


def test_update_replaces_existing_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HPX_DATA_DIR", str(tmp_path))
    update_copilot_env({"COPILOT_PROVIDER": "groq", "OPENAI_API_KEY": "first"})
    update_copilot_env({"OPENAI_API_KEY": "second"})
    apply_copilot_env_file_to_os_environ()
    assert read_env_file(tmp_path / "copilot.env")["OPENAI_API_KEY"] == "second"
