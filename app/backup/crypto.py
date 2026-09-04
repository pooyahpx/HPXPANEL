"""Optional Fernet encryption for panel backup archives."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from config import backup_settings

_ENCRYPTED_MAGIC = b"HPXB1:"


def encryption_enabled() -> bool:
    return bool((backup_settings.encryption_key or "").strip())


def _fernet() -> Fernet:
    secret = (backup_settings.encryption_key or "").strip()
    if not secret:
        raise RuntimeError("BACKUP_ENCRYPTION_KEY is not configured")
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def is_encrypted_archive(path: Path) -> bool:
    with path.open("rb") as handle:
        return handle.read(len(_ENCRYPTED_MAGIC)) == _ENCRYPTED_MAGIC


def encrypt_archive_inplace(path: Path) -> None:
    if not encryption_enabled():
        return
    plaintext = path.read_bytes()
    if plaintext.startswith(_ENCRYPTED_MAGIC):
        return
    token = _fernet().encrypt(plaintext)
    path.write_bytes(_ENCRYPTED_MAGIC + token)


def decrypt_archive_to(path: Path, target: Path) -> Path:
    raw = path.read_bytes()
    if not raw.startswith(_ENCRYPTED_MAGIC):
        if target != path:
            target.write_bytes(raw)
        return target
    try:
        plaintext = _fernet().decrypt(raw[len(_ENCRYPTED_MAGIC) :])
    except InvalidToken as exc:
        raise RuntimeError(
            "Backup is encrypted but BACKUP_ENCRYPTION_KEY is missing or incorrect"
        ) from exc
    target.write_bytes(plaintext)
    return target


def open_archive_bytes(path: Path) -> bytes:
    raw = path.read_bytes()
    if not raw.startswith(_ENCRYPTED_MAGIC):
        return raw
    try:
        return _fernet().decrypt(raw[len(_ENCRYPTED_MAGIC) :])
    except InvalidToken as exc:
        raise RuntimeError(
            "Backup is encrypted but BACKUP_ENCRYPTION_KEY is missing or incorrect"
        ) from exc
