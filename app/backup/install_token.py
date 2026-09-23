"""Short-lived install tokens so a fresh install can download a backup.

Tracks last-used IP / geo (datacenter = ISP) and supports revoke + enable/disable.
"""

from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.backup.service import _resolve_archive, get_backup_dir

_TOKENS_FILE = "install_tokens.json"
_DEFAULT_TTL_HOURS = 72


def _tokens_path() -> Path:
    return get_backup_dir() / _TOKENS_FILE


def _load() -> dict[str, dict]:
    path = _tokens_path()
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return {}
    return raw if isinstance(raw, dict) else {}


def _save(data: dict[str, dict]) -> None:
    path = _tokens_path()
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _parse_expires(value: Any) -> datetime | None:
    try:
        expires = datetime.fromisoformat(str(value or ""))
    except ValueError:
        return None
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    return expires


def _is_expired(row: dict, *, now: datetime | None = None) -> bool:
    expires = _parse_expires(row.get("expires_at"))
    if expires is None:
        return True
    return expires <= (now or datetime.now(UTC))


def _purge_expired(data: dict[str, dict]) -> dict[str, dict]:
    """Drop expired rows. Keep revoked/disabled so the owner can still audit them briefly."""
    now = datetime.now(UTC)
    kept: dict[str, dict] = {}
    for token, row in data.items():
        if not isinstance(row, dict):
            continue
        if _is_expired(row, now=now):
            continue
        kept[token] = row
    return kept


def create_install_token(backup_id: str, *, ttl_hours: int = _DEFAULT_TTL_HOURS) -> dict:
    """Create a download token bound to an existing backup archive."""
    archive = _resolve_archive(backup_id)
    if not archive.exists():
        raise FileNotFoundError(f"Backup archive not found: {backup_id}")

    data = _purge_expired(_load())
    token = secrets.token_urlsafe(24)
    expires = datetime.now(UTC) + timedelta(hours=max(1, min(int(ttl_hours), 168)))
    row = {
        "backup_id": backup_id,
        "filename": archive.name,
        "created_at": datetime.now(UTC).isoformat(),
        "expires_at": expires.isoformat(),
        "consumed": False,
        "enabled": True,
        "revoked": False,
        "use_count": 0,
        "last_used_at": None,
        "last_used_ip": None,
        "last_used_country": None,
        "last_used_country_code": None,
        "last_used_city": None,
        "last_used_isp": None,
        "last_used_asn": None,
    }
    data[token] = row
    _save(data)
    return {"token": token, **row}


def resolve_install_token(
    token: str,
    *,
    consume: bool = False,
    ip: str | None = None,
    geo: dict[str, Any] | None = None,
) -> Path:
    """Return archive path for a valid, enabled token. Optionally record usage + consume."""
    data = _purge_expired(_load())
    row = data.get(token)
    if not row:
        all_rows = _load()
        if token in all_rows:
            raise PermissionError("Install token expired or revoked")
        raise FileNotFoundError("Install token not found")

    if row.get("revoked"):
        raise PermissionError("Install token revoked")
    if row.get("enabled") is False:
        raise PermissionError("Install token disabled")
    if row.get("consumed"):
        raise PermissionError("Install token already used")

    backup_id = str(row["backup_id"])
    archive = _resolve_archive(backup_id)
    if not archive.exists():
        raise FileNotFoundError(f"Backup archive missing for token: {backup_id}")

    geo = geo or {}
    if ip:
        row["last_used_at"] = datetime.now(UTC).isoformat()
        row["last_used_ip"] = ip
        row["last_used_country"] = geo.get("country")
        row["last_used_country_code"] = geo.get("country_code")
        row["last_used_city"] = geo.get("city")
        row["last_used_isp"] = geo.get("isp")
        row["last_used_asn"] = geo.get("asn")
        row["use_count"] = int(row.get("use_count") or 0) + 1

    if consume:
        row["consumed"] = True

    data[token] = row
    _save(data)
    return archive


def list_install_tokens(*, include_revoked: bool = True) -> list[dict]:
    """Return token rows newest-first for the admin panel."""
    data = _purge_expired(_load())
    items: list[dict] = []
    for token, row in data.items():
        if not isinstance(row, dict):
            continue
        if not include_revoked and (row.get("revoked") or row.get("consumed")):
            continue
        items.append({"token": token, **row})
    items.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    return items


def set_install_token_enabled(token: str, *, enabled: bool) -> dict:
    data = _purge_expired(_load())
    row = data.get(token)
    if not row:
        raise FileNotFoundError("Install token not found")
    if row.get("revoked"):
        raise PermissionError("Install token revoked")
    row["enabled"] = bool(enabled)
    data[token] = row
    _save(data)
    return {"token": token, **row}


def revoke_install_token(token: str) -> dict:
    data = _load()
    row = data.get(token)
    if not row:
        raise FileNotFoundError("Install token not found")
    row["revoked"] = True
    row["enabled"] = False
    row["consumed"] = True
    data[token] = row
    _save(data)
    return {"token": token, **row}


def build_install_command(*, restore_url: str, database: str = "timescaledb") -> str:
    script = 'sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXPANEL/raw/main/scripts/hpxpanel.sh)" @'
    db = database if database in {"sqlite", "mysql", "mariadb", "postgresql", "timescaledb"} else "timescaledb"
    if db == "sqlite":
        return f'{script} install --restore-url "{restore_url}"'
    return f'{script} install --database {db} --restore-url "{restore_url}"'
