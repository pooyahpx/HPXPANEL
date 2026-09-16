"""SSH bootstrap for host-side HPXNODE update (installs serviced + pulls image)."""

from __future__ import annotations

import io
from typing import Any

# Pinned so panel-driven updates land on a known good host installer.
HOST_UPDATE_SCRIPT_URL = "https://github.com/pooyahpx/HPXNODE/raw/v0.6.1/scripts/install.sh"

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


def run_host_update_via_ssh(
    *,
    host: str,
    port: int,
    username: str,
    password: str | None = None,
    private_key: str | None = None,
    timeout: int = 600,
) -> str:
    """SSH to the node host and run ``hpx-node update -y`` (installs serviced).

    Returns combined stdout/stderr from the remote command.
    Raises ``ValueError`` for bad input and ``RuntimeError`` on SSH/command failure.
    """
    if not host.strip():
        raise ValueError("SSH host is required")
    if not username.strip():
        raise ValueError("SSH username is required")
    if not password and not private_key:
        raise ValueError("Provide SSH password or private key")
    if password and private_key:
        raise ValueError("Provide either SSH password or private key, not both")

    try:
        import paramiko
    except ImportError as exc:
        raise RuntimeError("paramiko is required for host SSH update") from exc

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs: dict[str, Any] = {
        "hostname": host.strip(),
        "port": port,
        "username": username.strip(),
        "timeout": 30,
        "allow_agent": False,
        "look_for_keys": False,
    }
    if private_key:
        key_file = io.StringIO(private_key.strip() + "\n")
        pkey = None
        for key_cls in (
            paramiko.Ed25519Key,
            paramiko.RSAKey,
            paramiko.ECDSAKey,
        ):
            try:
                key_file.seek(0)
                pkey = key_cls.from_private_key(key_file)
                break
            except Exception:
                continue
        if pkey is None:
            raise ValueError("Could not parse SSH private key (supports Ed25519/RSA/ECDSA)")
        connect_kwargs["pkey"] = pkey
    else:
        connect_kwargs["password"] = password

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
