"""Unit tests for panel backup dump URL / CLI helpers."""

from urllib.parse import urlparse

from app.backup import service as backup_service


def test_dump_database_url_rewrites_pgbouncer_port(monkeypatch):
    class _DB:
        url = "postgresql+asyncpg://user:p%40ss@127.0.0.1:6432/hpxpanel"
        is_postgresql = True

    monkeypatch.setattr(backup_service, "database_settings", _DB())
    url = backup_service._dump_database_url()
    parsed = urlparse(url)
    assert parsed.scheme == "postgresql"
    assert parsed.port == 5432
    assert parsed.hostname == "127.0.0.1"
    assert parsed.path == "/hpxpanel"
    assert "p%40ss" in url or "p@ss" in url


def test_dump_database_url_keeps_direct_postgres_port(monkeypatch):
    class _DB:
        url = "postgresql+asyncpg://user:secret@timescaledb:5432/hpxpanel"
        is_postgresql = True

    monkeypatch.setattr(backup_service, "database_settings", _DB())
    url = backup_service._dump_database_url()
    assert urlparse(url).port == 5432
    assert "timescaledb" in url


def test_require_cli_missing_binary(monkeypatch):
    monkeypatch.setattr(backup_service.shutil, "which", lambda _name: None)
    try:
        backup_service._require_cli("pg_dump")
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "postgresql-client-17" in str(exc)
