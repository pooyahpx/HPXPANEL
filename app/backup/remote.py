from __future__ import annotations

from pathlib import Path

from app.models.backup import BackupRemoteSftp
from config import backup_settings


def upload_backup_sftp(archive_path: Path, remote: BackupRemoteSftp) -> None:
    if not remote.host or not remote.username:
        raise ValueError("SFTP host and username are required")

    password = backup_settings.sftp_password
    if not password and not backup_settings.sftp_private_key_path:
        raise ValueError("Set BACKUP_SFTP_PASSWORD or BACKUP_SFTP_PRIVATE_KEY_PATH in .env")

    try:
        import paramiko
    except ImportError as exc:
        raise RuntimeError("paramiko is required for SFTP backup upload") from exc

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs: dict = {
        "hostname": remote.host,
        "port": remote.port,
        "username": remote.username,
        "timeout": 30,
    }
    if backup_settings.sftp_private_key_path:
        connect_kwargs["key_filename"] = backup_settings.sftp_private_key_path
    else:
        connect_kwargs["password"] = password

    client.connect(**connect_kwargs)
    try:
        sftp = client.open_sftp()
        try:
            remote_dir = remote.remote_path.rstrip("/") or "/var/backups/hpxpanel"
            _ensure_remote_dir(sftp, remote_dir)
            remote_file = f"{remote_dir}/{archive_path.name}"
            sftp.put(str(archive_path), remote_file)
        finally:
            sftp.close()
    finally:
        client.close()


def _ensure_remote_dir(sftp, path: str) -> None:
    parts = [part for part in path.split("/") if part]
    current = ""
    for part in parts:
        current = f"{current}/{part}"
        try:
            sftp.stat(current)
        except OSError:
            sftp.mkdir(current)
