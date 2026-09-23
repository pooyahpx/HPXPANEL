"""Unit tests for backup install-token tracking / revoke."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.backup import install_token as it


@pytest.fixture()
def token_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(it, "get_backup_dir", lambda: tmp_path)
    monkeypatch.setattr(it, "_resolve_archive", lambda backup_id: tmp_path / f"{backup_id}.zip")
    archive = tmp_path / "bk1.zip"
    archive.write_bytes(b"zip")
    return tmp_path


def test_create_and_list_token(token_dir: Path):
    row = it.create_install_token("bk1", ttl_hours=24)
    assert row["token"]
    assert row["enabled"] is True
    items = it.list_install_tokens()
    assert len(items) == 1
    assert items[0]["backup_id"] == "bk1"


def test_resolve_records_ip_and_geo(token_dir: Path):
    row = it.create_install_token("bk1")
    path = it.resolve_install_token(
        row["token"],
        ip="203.0.113.10",
        geo={"country": "Germany", "country_code": "DE", "city": "Falkenstein", "isp": "Hetzner Online GmbH", "asn": "AS24940"},
    )
    assert path.exists()
    listed = it.list_install_tokens()[0]
    assert listed["last_used_ip"] == "203.0.113.10"
    assert listed["last_used_isp"] == "Hetzner Online GmbH"
    assert listed["use_count"] == 1


def test_disable_blocks_download(token_dir: Path):
    row = it.create_install_token("bk1")
    it.set_install_token_enabled(row["token"], enabled=False)
    with pytest.raises(PermissionError, match="disabled"):
        it.resolve_install_token(row["token"], ip="1.1.1.1")


def test_revoke_blocks_download(token_dir: Path):
    row = it.create_install_token("bk1")
    it.revoke_install_token(row["token"])
    with pytest.raises(PermissionError):
        it.resolve_install_token(row["token"], ip="1.1.1.1")
    listed = it.list_install_tokens()[0]
    assert listed["revoked"] is True
    assert listed["enabled"] is False


def test_expired_token_purged(token_dir: Path):
    row = it.create_install_token("bk1", ttl_hours=1)
    data = it._load()
    data[row["token"]]["expires_at"] = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    it._save(data)
    with pytest.raises(PermissionError, match="expired"):
        it.resolve_install_token(row["token"])
