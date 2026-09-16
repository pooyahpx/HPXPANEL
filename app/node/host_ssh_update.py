"""SSH bootstrap for host-side HPXNODE update (installs serviced + pulls image)."""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any

# Pinned so panel-driven updates land on a known good host installer.
HOST_UPDATE_SCRIPT_URL = "https://github.com/pooyahpx/HPXNODE/raw/v0.6.2/scripts/install.sh"

HOST_UPDATE_REMOTE_SCRIPT = f"""set -euo pipefail
URL='{HOST_UPDATE_SCRIPT_URL}'
if [ "$(id -u)" -eq 0 ]; then
  bash -c "$(curl -fsSL "$URL")" @ update -y
else
  if ! sudo -n true 2>/dev/null; then
    echo "sudo requires passwordless sudo for non-root SSH users" >&2
    exit 1
  fi
  sudo bash -c "$(curl -fsSL "$URL")" @ update -y
fi
"""


def _load_pkey_from_text(private_key: str):
    import paramiko

    key_file = io.StringIO(private_key.strip() + "\n")
    parse_errors: list[str] = []
    for key_cls in (
        paramiko.Ed25519Key,
        paramiko.RSAKey,
        paramiko.ECDSAKey,
    ):
        try:
            key_file.seek(0)
            return key_cls.from_private_key(key_file)
        except Exception as exc:
            parse_errors.append(f"{key_cls.__name__}: {exc}")
    detail = "; ".join(parse_errors) if parse_errors else "unsupported key type"
    raise ValueError(f"Could not parse SSH private key ({detail})")


def _connect_and_run(
    *,
    host: str,
    port: int,
    username: str,
    password: str | None = None,
    private_key: str | None = None,
    look_for_keys: bool = False,
    allow_agent: bool = False,
    timeout: int = 600,
) -> str:
    import paramiko

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs: dict[str, Any] = {
        "hostname": host.strip(),
        "port": port,
        "username": username.strip(),
        "timeout": 30,
        "allow_agent": allow_agent,
        "look_for_keys": look_for_keys,
    }
    if private_key:
        connect_kwargs["pkey"] = _load_pkey_from_text(private_key)
        connect_kwargs["allow_agent"] = False
        connect_kwargs["look_for_keys"] = False
    elif password:
        connect_kwargs["password"] = password
        connect_kwargs["allow_agent"] = False
        connect_kwargs["look_for_keys"] = False

    try:
        client.connect(**connect_kwargs)
    except Exception as exc:
        raise RuntimeError(f"SSH connection failed: {exc}") from exc

    try:
        _stdin, stdout, stderr = client.exec_command(HOST_UPDATE_REMOTE_SCRIPT, timeout=timeout, get_pty=True)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        code = stdout.channel.recv_exit_status()
        combined = (out + ("\n" + err if err.strip() else "")).strip()
        if code != 0:
            raise RuntimeError(combined or f"Host update failed with exit code {code}")
        return combined or "Host update completed"
    finally:
        client.close()


def run_host_update_via_ssh(
    *,
    host: str,
    port: int,
    username: str,
    password: str | None = None,
    private_key: str | None = None,
    timeout: int = 600,
) -> str:
    """SSH to the node host and run ``hpx-node update -y`` (installs serviced)."""
    if not host.strip():
        raise ValueError("SSH host is required")
    if not username.strip():
        raise ValueError("SSH username is required")
    if not password and not private_key:
        raise ValueError("Provide SSH password or private key")
    if password and private_key:
        raise ValueError("Provide either SSH password or private key, not both")

    try:
        import paramiko  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("paramiko is required for host SSH update") from exc

    return _connect_and_run(
        host=host,
        port=port,
        username=username,
        password=password,
        private_key=private_key,
        timeout=timeout,
    )


def run_host_update_auto(
    *,
    host: str,
    port: int | None = None,
    username: str | None = None,
    timeout: int = 600,
) -> str:
    """Best-effort host update with zero UI prompts.

    Auth order:
    1. ``NODE_SSH_PRIVATE_KEY`` / ``NODE_SSH_PRIVATE_KEY_PATH`` / ``NODE_SSH_PASSWORD`` env
    2. Local SSH agent + ``~/.ssh`` keys (passwordless)
    """
    if not host.strip():
        raise ValueError("SSH host is required")

    try:
        import paramiko  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("paramiko is required for host SSH update") from exc

    # Prefer explicit args, then env (same vars as NodeHostSshSettings).
    ssh_port = int(port or os.getenv("NODE_SSH_PORT") or 22)
    ssh_user = (username or os.getenv("NODE_SSH_USERNAME") or "root").strip()
    env_password = (os.getenv("NODE_SSH_PASSWORD") or "").strip() or None
    env_key = (os.getenv("NODE_SSH_PRIVATE_KEY") or "").strip() or None
    key_path = (os.getenv("NODE_SSH_PRIVATE_KEY_PATH") or "").strip()
    if not env_key and key_path:
        path = Path(key_path)
        if path.is_file():
            env_key = path.read_text(encoding="utf-8", errors="replace")

    errors: list[str] = []

    if env_key or env_password:
        try:
            return _connect_and_run(
                host=host,
                port=ssh_port,
                username=ssh_user,
                password=None if env_key else env_password,
                private_key=env_key,
                timeout=timeout,
            )
        except Exception as exc:
            errors.append(f"env credentials: {exc}")

    try:
        return _connect_and_run(
            host=host,
            port=ssh_port,
            username=ssh_user,
            look_for_keys=True,
            allow_agent=True,
            timeout=timeout,
        )
    except Exception as exc:
        errors.append(f"ssh keys/agent: {exc}")

    detail = " | ".join(errors) if errors else "no SSH auth available"
    raise RuntimeError(
        "Could not reach the node update service and could not SSH to the host "
        f"({detail}). On the panel host set NODE_SSH_PRIVATE_KEY or NODE_SSH_PASSWORD "
        "(or passwordless root SSH to the node), then click Update Node again."
    )
