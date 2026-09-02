"""Persist Copilot env vars under HPX_DATA_DIR (writable in Docker)."""

from __future__ import annotations

import os
import re
from pathlib import Path

COPILOT_ENV_KEYS = (
    "COPILOT_ENABLED",
    "COPILOT_PROVIDER",
    "OPENAI_API_KEY",
    "COPILOT_MODEL",
    "COPILOT_BASE_URL",
)

_ENV_LINE_RE = re.compile(r"^[ \t]*#?[ \t]*([A-Za-z_][A-Za-z0-9_]*)[ \t]*=[ \t]*(.*)$")


def copilot_env_path() -> Path:
    data_dir = Path(os.environ.get("HPX_DATA_DIR", "/var/lib/hpxpanel"))
    return data_dir / "copilot.env"


def mask_secret(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if len(value) <= 8:
        return "••••••••"
    return f"{value[:4]}…{value[-4:]}"


def _format_env_line(key: str, value: str) -> str:
    if not value:
        return f"{key} ="
    if any(ch in value for ch in ' \t#"\\'):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'{key} = "{escaped}"'
    return f"{key} = {value}"


def _parse_env_value(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        return ""
    if raw[0] in {'"', "'"} and raw[-1] == raw[0]:
        inner = raw[1:-1]
        return inner.replace('\\"', '"').replace("\\\\", "\\")
    if " #" in raw:
        raw = raw.split(" #", 1)[0].rstrip()
    return raw


def read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _ENV_LINE_RE.match(line)
        if not match:
            continue
        key, raw_value = match.groups()
        values[key] = _parse_env_value(raw_value)
    return values


def write_env_file(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = read_env_file(path) if path.is_file() else {}
    merged = {**existing, **values}
    lines = [_format_env_line(key, merged[key]) for key in COPILOT_ENV_KEYS if key in merged]
    content = "\n".join(lines)
    if content:
        content += "\n"
    path.write_text(content, encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def apply_copilot_env_file_to_os_environ(path: Path | None = None) -> None:
    env_path = path or copilot_env_path()
    for key, value in read_env_file(env_path).items():
        if key in COPILOT_ENV_KEYS:
            os.environ[key] = value


def update_copilot_env(values: dict[str, str]) -> Path:
    path = copilot_env_path()
    write_env_file(path, values)
    apply_copilot_env_file_to_os_environ(path)
    return path
