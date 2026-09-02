from pathlib import Path

import pytest
from fastapi import status

from tests.api import client
from tests.api.helpers import auth_headers


@pytest.fixture
def copilot_env_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HPX_DATA_DIR", str(tmp_path))
    yield tmp_path


def test_copilot_settings_update(access_token, copilot_env_dir: Path):
    response = client.put(
        "/api/copilot/settings",
        headers=auth_headers(access_token),
        json={
            "provider": "groq",
            "api_key": "gsk_test_integration_key_1234",
            "model": "openai/gpt-oss-20b",
            "enabled": True,
        },
    )
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["configured"] is True
    assert body["provider"] == "groq"
    assert body["saved"] is True
    assert "gsk_" in body["api_key_masked"]

    env_file = copilot_env_dir / "copilot.env"
    assert env_file.is_file()
    assert "gsk_test_integration_key_1234" in env_file.read_text(encoding="utf-8")

    status_response = client.get("/api/copilot/status", headers=auth_headers(access_token))
    assert status_response.status_code == status.HTTP_200_OK
    assert status_response.json()["configured"] is True
