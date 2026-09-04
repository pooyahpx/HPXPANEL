from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

from app.backup.crypto import (
    decrypt_archive_to,
    encrypt_archive_inplace,
    encryption_enabled,
    is_encrypted_archive,
    open_archive_bytes,
)
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


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _create_zip(source_dir: Path, archive_path: Path) -> int:
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for file_path in sorted(source_dir.rglob("*")):
            if file_path.is_file():
                archive.write(file_path, arcname=file_path.relative_to(source_dir).as_posix())
    return archive_path.stat().st_size


def _zipfile_from_archive(archive_path: Path) -> zipfile.ZipFile:
    payload = open_archive_bytes(archive_path)
    return zipfile.ZipFile(io.BytesIO(payload), "r")


def _read_manifest_from_zip(archive_path: Path) -> BackupManifest:
    with _zipfile_from_archive(archive_path) as archive:
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
                    encrypted=manifest.encrypted or is_encrypted_archive(archive_path),
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
                    encrypted=is_encrypted_archive(archive_path),
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
        encrypted = encryption_enabled()
        remote_error = ""
        remote_uploaded = False

        manifest = BackupManifest(
            id=backup_id,
            created_at=datetime.now(UTC),
            panel_version=__version__,
            database_engine=_database_engine(),
            database_file=db_file.name,
            size_bytes=0,
            sha256=_sha256_file(db_file),
            encrypted=encrypted,
        )
        (work_dir / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        size_bytes = _create_zip(work_dir, archive_path)
        manifest.size_bytes = size_bytes

        if encrypted:
            encrypt_archive_inplace(archive_path)
            manifest.size_bytes = archive_path.stat().st_size

        if upload_remote and config.upload_to_remote and config.remote.enabled:
            from app.backup.remote import upload_backup_sftp

            try:
                upload_backup_sftp(archive_path, config.remote)
                remote_uploaded = True
            except Exception as exc:
                remote_error = str(exc)

        manifest.remote_uploaded = remote_uploaded
        manifest.remote_error = remote_error

        if not encrypted:
            # Refresh plaintext archive so remote status is stored inside the zip.
            (work_dir / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
            archive_path.unlink(missing_ok=True)
            manifest.size_bytes = _create_zip(work_dir, archive_path)

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


def validate_backup(backup_id: str) -> tuple[BackupManifest, list[str]]:
    """Validate archive integrity without restoring. Returns manifest and check notes."""
    archive_path = _resolve_archive(backup_id)
    checks: list[str] = []
    encrypted = is_encrypted_archive(archive_path)
    if encrypted:
        checks.append("archive is encrypted")
        if not encryption_enabled():
            raise RuntimeError("Backup is encrypted but BACKUP_ENCRYPTION_KEY is not configured")
    else:
        checks.append("archive is plaintext zip")

    plaintext = open_archive_bytes(archive_path)

    with zipfile.ZipFile(io.BytesIO(plaintext), "r") as archive:
        names = set(archive.namelist())
        if "manifest.json" not in names:
            raise ValueError("manifest.json missing from backup archive")
        checks.append("manifest.json present")
        manifest = BackupManifest.model_validate(json.loads(archive.read("manifest.json")))
        db_name = manifest.database_file
        if db_name not in names:
            raise ValueError(f"Database dump missing from archive: {db_name}")
        checks.append(f"database dump present ({db_name})")
        raw_db = archive.read(db_name)
        if not raw_db:
            raise ValueError(f"Database dump is empty: {db_name}")
        checks.append(f"database dump size={len(raw_db)} bytes")
        digest = _sha256_bytes(raw_db)
        if manifest.sha256 and manifest.sha256 != digest:
            raise ValueError(f"SHA256 mismatch: expected {manifest.sha256}, got {digest}")
        checks.append(f"sha256 ok ({digest[:12]}…)")
        if manifest.database_engine == "sqlite":
            if not raw_db.startswith(b"SQLite format 3"):
                raise ValueError("SQLite dump does not look like a valid database file")
            checks.append("sqlite header valid")
        elif manifest.database_engine == "postgresql":
            if b"PostgreSQL" not in raw_db[:4096] and b"CREATE" not in raw_db[:4096]:
                raise ValueError("PostgreSQL dump does not look restorable")
            checks.append("postgresql dump looks restorable")
        elif manifest.database_engine == "mysql":
            checks.append("mysql dump present (panel restore still unsupported)")

    if manifest.encrypted != encrypted:
        checks.append("encrypted flag reconciled from file header")
        manifest.encrypted = encrypted
    return manifest, checks


def restore_backup(backup_id: str, *, dry_run: bool = False) -> list[str]:
    manifest, checks = validate_backup(backup_id)
    if dry_run:
        checks.append("dry-run only — no database writes")
        return checks

    if not backup_settings.allow_panel_restore:
        raise RuntimeError(
            "Panel restore is disabled. Set BACKUP_ALLOW_PANEL_RESTORE=true or use hpxpanel.sh restore on the server."
        )

    archive_path = _resolve_archive(backup_id)
    engine = manifest.database_engine

    with tempfile.TemporaryDirectory() as tmp:
        plain_zip = Path(tmp) / "backup.zip"
        decrypt_archive_to(archive_path, plain_zip)
        with zipfile.ZipFile(plain_zip, "r") as archive:
            if engine == "sqlite":
                db_name = manifest.database_file
                target = _sqlite_db_path()
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(db_name) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                return checks

            if engine == "postgresql":
                sql_name = manifest.database_file
                temp_sql = Path(tmp) / f"restore_{backup_id}.sql"
                with archive.open(sql_name) as src, temp_sql.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                _run_command(["psql", _sync_database_url(), "-v", "ON_ERROR_STOP=1", "-f", str(temp_sql)])
                return checks

            if engine == "mysql":
                raise ValueError(
                    "MySQL restore from the panel is not supported yet. Download the archive and restore with mysqldump on the server."
                )

    raise ValueError(f"Unsupported backup database engine: {engine}")


async def create_backup_async(config: BackupConfig, *, upload_remote: bool = True) -> BackupManifest:
    return await asyncio.to_thread(create_backup, config, upload_remote=upload_remote)


async def restore_backup_async(backup_id: str, *, dry_run: bool = False) -> list[str]:
    return await asyncio.to_thread(restore_backup, backup_id, dry_run=dry_run)


async def validate_backup_async(backup_id: str) -> tuple[BackupManifest, list[str]]:
    return await asyncio.to_thread(validate_backup, backup_id)
