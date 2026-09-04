import io
import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from app.backup import crypto as backup_crypto, service as backup_service
from app.models.backup import BackupConfig


def test_backup_config_defaults():
    config = BackupConfig()
    assert config.auto_enabled is False
    assert config.schedule_hours == 24
    assert config.remote.port == 22


def _seed_sqlite(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE demo (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO demo(name) VALUES ('hpx')")
        conn.commit()


@pytest.fixture
def backup_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "panel.db"
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    _seed_sqlite(db_path)

    monkeypatch.setattr(backup_service.database_settings, "url", f"sqlite+aiosqlite:///{db_path.as_posix()}")
    # DatabaseSettings.is_* are cached_property and keep the process CI engine
    # (mysql/postgres) unless the cache is cleared after the URL patch.
    for attr in ("is_postgresql", "is_mysql", "is_sqlite"):
        backup_service.database_settings.__dict__.pop(attr, None)
    monkeypatch.setattr(backup_service.backup_settings, "directory", str(backup_dir))
    monkeypatch.setattr(backup_service.backup_settings, "allow_panel_restore", True)
    monkeypatch.setattr(backup_service.backup_settings, "encryption_key", "")
    monkeypatch.setattr(backup_crypto.backup_settings, "directory", str(backup_dir))
    monkeypatch.setattr(backup_crypto.backup_settings, "encryption_key", "")
    return db_path, backup_dir


def test_create_and_dry_run_restore(backup_env):
    _db_path, _backup_dir = backup_env
    manifest = backup_service.create_backup(BackupConfig(upload_to_remote=False), upload_remote=False)
    assert manifest.database_engine == "sqlite"
    assert manifest.sha256
    assert not manifest.encrypted

    checks = backup_service.restore_backup(manifest.id, dry_run=True)
    assert any("sha256 ok" in item for item in checks)
    assert any("sqlite header valid" in item for item in checks)


def test_encrypted_backup_roundtrip(backup_env, monkeypatch: pytest.MonkeyPatch):
    db_path, _backup_dir = backup_env
    monkeypatch.setattr(backup_service.backup_settings, "encryption_key", "test-backup-secret")
    monkeypatch.setattr(backup_crypto.backup_settings, "encryption_key", "test-backup-secret")

    manifest = backup_service.create_backup(BackupConfig(upload_to_remote=False), upload_remote=False)
    archive = backup_service._resolve_archive(manifest.id)
    assert backup_crypto.is_encrypted_archive(archive)
    assert manifest.encrypted is True

    checks = backup_service.restore_backup(manifest.id, dry_run=True)
    assert any("archive is encrypted" in item for item in checks)

    # Corrupt live DB then restore for real.
    db_path.write_bytes(b"broken")
    backup_service.restore_backup(manifest.id, dry_run=False)
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT name FROM demo").fetchone()[0] == "hpx"


def test_validate_rejects_tampered_dump(backup_env):
    manifest = backup_service.create_backup(BackupConfig(upload_to_remote=False), upload_remote=False)
    archive = backup_service._resolve_archive(manifest.id)
    with zipfile.ZipFile(archive, "r") as zf:
        payload = {name: zf.read(name) for name in zf.namelist()}
    payload[manifest.database_file] = b"SQLite format 3\x00tampered"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in payload.items():
            if name == "manifest.json":
                meta = json.loads(data)
                zf.writestr(name, json.dumps(meta))
            else:
                zf.writestr(name, data)
    archive.write_bytes(buf.getvalue())

    with pytest.raises(ValueError, match="SHA256 mismatch"):
        backup_service.validate_backup(manifest.id)
