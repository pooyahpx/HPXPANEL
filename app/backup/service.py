from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

from app.models.backup import BackupConfig, BackupListItem, BackupManifest, BackupStatus
from app.version import __version__
from config import backup_settings, database_settings

_STATE: dict = {
    "status": BackupStatus.idle,
    "last_error": "",
    "last_success_at": None,
}


def get_state() -> dict:
    return dict(_STATE)


def _set_state(*, status: BackupStatus, error: str = "", success_at: datetime | None = None) -> None:
    _STATE["status"] = status
    if error:
        _STATE["last_error"] = error
    if success_at is not None:
        _STATE["last_success_at"] = success_at
        _STATE["last_error"] = ""


def get_backup_dir() -> Path:
    path = Path(backup_settings.directory).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _lock_path() -> Path:
    return get_backup_dir() / ".backup.lock"


def _sqlite_db_path() -> Path:
    parsed = urlparse(database_settings.url.replace("+aiosqlite", ""))
    if parsed.path in {"", "/"}:
        raise ValueError("Could not resolve SQLite database path from SQLALCHEMY_DATABASE_URL")
    raw = unquote(parsed.path)
    if os.name == "nt" and raw.startswith("/") and len(raw) > 2 and raw[2] == ":":
        raw = raw[1:]
    return Path(raw)


def _database_engine() -> str:
    if database_settings.is_postgresql:
        return "postgresql"
    if database_settings.is_mysql:
        return "mysql"
    if database_settings.is_sqlite:
        return "sqlite"
    return "unknown"


def _sync_database_url() -> str:
    url = database_settings.url
    for needle in ("+asyncpg", "+aiosqlite", "+asyncmy"):
        url = url.replace(needle, "")
    return url


def _dump_sqlite(target: Path) -> Path:
    source = _sqlite_db_path()
    if not source.exists():
        raise FileNotFoundError(f"SQLite database not found: {source}")
    output = target / "database.sqlite3"
    with sqlite3.connect(source) as src, sqlite3.connect(output) as dst:
        src.backup(dst)
    return output


def _run_command(command: list[str], *, env: dict | None = None) -> None:
    result = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "command failed").strip()
        raise RuntimeError(stderr[:2000])


def _dump_postgresql(target: Path) -> Path:
    output = target / "database.sql"
    command = ["pg_dump", "--no-owner", "--no-acl", "--format=plain", "--file", str(output), _sync_database_url()]
    _run_command(command)
    return output


def _dump_mysql(target: Path) -> Path:
    output = target / "database.sql"
    command = ["mysqldump", "--single-transaction", "--result-file", str(output), _sync_database_url()]
    _run_command(command)
    return output


def _dump_database(work_dir: Path) -> Path:
    engine = _database_engine()
    if engine == "sqlite":
        return _dump_sqlite(work_dir)
    if engine == "postgresql":
        return _dump_postgresql(work_dir)
    if engine == "mysql":
        return _dump_mysql(work_dir)
    raise ValueError(f"Unsupported database engine for backup: {engine}")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _create_zip(source_dir: Path, archive_path: Path) -> int:
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for file_path in sorted(source_dir.rglob("*")):
            if file_path.is_file():
                archive.write(file_path, arcname=file_path.relative_to(source_dir).as_posix())
    return archive_path.stat().st_size


def _read_manifest_from_zip(archive_path: Path) -> BackupManifest:
    with zipfile.ZipFile(archive_path, "r") as archive:
        raw = archive.read("manifest.json")
    data = json.loads(raw.decode("utf-8"))
    return BackupManifest.model_validate(data)


def list_backups() -> list[BackupListItem]:
    items: list[BackupListItem] = []
    for archive_path in sorted(get_backup_dir().glob("hpxpanel_*.zip"), reverse=True):
        try:
            manifest = _read_manifest_from_zip(archive_path)
            items.append(
                BackupListItem(
                    id=manifest.id,
                    created_at=manifest.created_at,
                    panel_version=manifest.panel_version,
                    database_engine=manifest.database_engine,
                    size_bytes=manifest.size_bytes,
                    sha256=manifest.sha256,
                    remote_uploaded=manifest.remote_uploaded,
                    filename=archive_path.name,
                )
            )
        except Exception:
            stat = archive_path.stat()
            items.append(
                BackupListItem(
                    id=archive_path.stem,
                    created_at=datetime.fromtimestamp(stat.st_mtime, UTC),
                    panel_version="unknown",
                    database_engine="unknown",
                    size_bytes=stat.st_size,
                    sha256="",
                    filename=archive_path.name,
                )
            )
    return items


def _apply_retention(config: BackupConfig) -> None:
    archives = sorted(get_backup_dir().glob("hpxpanel_*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)
    for stale in archives[config.local_retention :]:
        stale.unlink(missing_ok=True)


def _resolve_archive(backup_id: str) -> Path:
    archive_path = get_backup_dir() / f"{backup_id}.zip"
    if not archive_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_id}")
    return archive_path


def create_backup(config: BackupConfig, *, upload_remote: bool = True) -> BackupManifest:
    if _lock_path().exists():
        raise RuntimeError("Another backup is already running")

    _lock_path().write_text(str(os.getpid()), encoding="utf-8")
    _set_state(status=BackupStatus.running)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_id = f"hpxpanel_{timestamp}"
    work_dir = get_backup_dir() / f".work_{backup_id}"
    archive_path = get_backup_dir() / f"{backup_id}.zip"
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        db_file = _dump_database(work_dir)
        manifest = BackupManifest(
            id=backup_id,
            created_at=datetime.now(UTC),
            panel_version=__version__,
            database_engine=_database_engine(),
            database_file=db_file.name,
            size_bytes=0,
            sha256="",
        )
        (work_dir / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        size_bytes = _create_zip(work_dir, archive_path)
        manifest.size_bytes = size_bytes
        manifest.sha256 = _sha256_file(archive_path)

        remote_error = ""
        remote_uploaded = False
        if upload_remote and config.upload_to_remote and config.remote.enabled:
            from app.backup.remote import upload_backup_sftp

            try:
                upload_backup_sftp(archive_path, config.remote)
                remote_uploaded = True
            except Exception as exc:
                remote_error = str(exc)

        manifest.remote_uploaded = remote_uploaded
        manifest.remote_error = remote_error

        with zipfile.ZipFile(archive_path, "a", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", manifest.model_dump_json(indent=2))

        _apply_retention(config)
        _set_state(status=BackupStatus.success, success_at=datetime.now(UTC))
        return manifest
    except Exception as exc:
        _set_state(status=BackupStatus.failed, error=str(exc))
        archive_path.unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        _lock_path().unlink(missing_ok=True)
        if _STATE["status"] == BackupStatus.running:
            _set_state(status=BackupStatus.idle)


def restore_backup(backup_id: str) -> None:
    if not backup_settings.allow_panel_restore:
        raise RuntimeError("Panel restore is disabled. Set BACKUP_ALLOW_PANEL_RESTORE=true or use hpxpanel.sh restore on the server.")

    archive_path = _resolve_archive(backup_id)
    manifest = _read_manifest_from_zip(archive_path)
    engine = manifest.database_engine

    with zipfile.ZipFile(archive_path, "r") as archive:
        if engine == "sqlite":
            db_name = manifest.database_file
            target = _sqlite_db_path()
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(db_name) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            return

        if engine == "postgresql":
            sql_name = manifest.database_file
            temp_sql = get_backup_dir() / f".restore_{backup_id}.sql"
            with archive.open(sql_name) as src, temp_sql.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            _run_command(["psql", _sync_database_url(), "-v", "ON_ERROR_STOP=1", "-f", str(temp_sql)])
            temp_sql.unlink(missing_ok=True)
            return

        if engine == "mysql":
            raise ValueError("MySQL restore from the panel is not supported yet. Download the archive and restore with mysqldump on the server.")

    raise ValueError(f"Unsupported backup database engine: {engine}")


async def create_backup_async(config: BackupConfig, *, upload_remote: bool = True) -> BackupManifest:
    return await asyncio.to_thread(create_backup, config, upload_remote=upload_remote)


async def restore_backup_async(backup_id: str) -> None:
    await asyncio.to_thread(restore_backup, backup_id)
