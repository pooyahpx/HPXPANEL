"""Helpers shared by panel importers."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

_USERNAME_SAFE = re.compile(r"[^a-zA-Z0-9_\-.]")


def sanitize_username(raw: str, *, fallback: str = "user") -> str:
    value = (raw or "").strip()
    value = value.replace("@", "_at_").replace(" ", "_")
    value = _USERNAME_SAFE.sub("_", value)
    value = value.strip("._-") or fallback
    return value[:128]


def parse_json_obj(value: Any, default: Any = None) -> Any:
    if value is None:
        return default if default is not None else {}
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="ignore")
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return default if default is not None else {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return default if default is not None else {}
    return default if default is not None else {}


def as_datetime(value: Any) -> datetime | None:
    if value in (None, "", 0, "0"):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, (int, float)):
        # Sanaei expiry_time is ms; PasarGuard may store unix seconds
        ts = float(value)
        if ts > 1_000_000_000_000:  # ms
            ts /= 1000.0
        if ts <= 0:
            return None
        return datetime.fromtimestamp(ts, tz=UTC)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            if text.isdigit():
                return as_datetime(int(text))
            # Accept both "...Z" and "...+00:00"
            normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
            dt = datetime.fromisoformat(normalized)
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except ValueError:
            return None
    return None


def coerce_uuid(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None


def unique_name(base: str, existing: set[str]) -> str:
    if base not in existing:
        existing.add(base)
        return base
    idx = 2
    while True:
        candidate = f"{base}_{idx}"
        if len(candidate) > 128:
            candidate = f"{base[:120]}_{idx}"
        if candidate not in existing:
            existing.add(candidate)
            return candidate
        idx += 1
