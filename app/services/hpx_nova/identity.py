"""Noise-compatible X25519 identities for HPX Nova Tunnel Engine configs."""

from __future__ import annotations

import base64
import json
import secrets

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _keypair() -> tuple[str, str]:
    private = X25519PrivateKey.generate()
    secret = private.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return _b64(secret), _b64(public)


def mint_nova_identity() -> dict[str, str]:
    iran_secret, iran_public = _keypair()
    abroad_secret, abroad_public = _keypair()
    return {
        "token": _b64(secrets.token_bytes(32)),
        "iran_secret": iran_secret,
        "iran_public": iran_public,
        "abroad_secret": abroad_secret,
        "abroad_public": abroad_public,
        "ws_credential": secrets.token_urlsafe(24),
    }


def identity_to_json(identity: dict[str, str]) -> str:
    return json.dumps(identity, separators=(",", ":"), sort_keys=True)


def identity_from_json(raw: str) -> dict[str, str]:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise TypeError("invalid nova identity")
    return {str(k): str(v) for k, v in data.items()}
