"""WebAuthn (passkey / hardware key) helpers for admin MFA."""

from __future__ import annotations

import json
import secrets
import time
from typing import Any
from urllib.parse import urlparse

from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from config import auth_settings, cors_settings, telegram_env_settings

_CHALLENGE_TTL_SECONDS = 300
_challenges: dict[str, tuple[float, dict[str, Any]]] = {}


def _purge_expired_challenges() -> None:
    now = time.monotonic()
    expired = [key for key, (expires_at, _) in _challenges.items() if expires_at <= now]
    for key in expired:
        _challenges.pop(key, None)


def store_challenge(kind: str, admin_id: int, challenge: bytes, extra: dict[str, Any] | None = None) -> str:
    _purge_expired_challenges()
    token = secrets.token_urlsafe(24)
    payload = {"kind": kind, "admin_id": admin_id, "challenge": challenge, **(extra or {})}
    _challenges[token] = (time.monotonic() + _CHALLENGE_TTL_SECONDS, payload)
    return token


def pop_challenge(token: str, *, kind: str, admin_id: int) -> dict[str, Any] | None:
    _purge_expired_challenges()
    entry = _challenges.pop(token, None)
    if entry is None:
        return None
    _, payload = entry
    if payload.get("kind") != kind or payload.get("admin_id") != admin_id:
        return None
    return payload


def resolve_rp_id(request_host: str | None = None) -> str:
    configured = (auth_settings.webauthn_rp_id or "").strip()
    if configured:
        return configured
    public_url = (telegram_env_settings.panel_public_url or "").strip()
    if public_url:
        host = urlparse(public_url).hostname
        if host:
            return host
    if request_host:
        return request_host.split(":")[0]
    return "localhost"


def resolve_origin(request_origin: str | None = None) -> str:
    configured = (auth_settings.webauthn_origin or "").strip()
    if configured:
        return configured
    public_url = (telegram_env_settings.panel_public_url or "").strip().rstrip("/")
    if public_url:
        return public_url
    if request_origin and request_origin != "null":
        return request_origin
    origins = cors_settings.allowed_origins
    for origin in origins:
        if origin and origin != "*":
            return origin
    return "http://localhost:5173"


def resolve_rp_name() -> str:
    return (auth_settings.webauthn_rp_name or "HPXPANEL").strip() or "HPXPANEL"


def build_registration_options(
    *,
    admin_id: int,
    username: str,
    existing_credential_ids: list[str],
    request_host: str | None = None,
) -> tuple[str, dict[str, Any]]:
    exclude = [PublicKeyCredentialDescriptor(id=base64url_to_bytes(cred_id)) for cred_id in existing_credential_ids]
    options = generate_registration_options(
        rp_id=resolve_rp_id(request_host),
        rp_name=resolve_rp_name(),
        user_id=str(admin_id).encode("utf-8"),
        user_name=username,
        user_display_name=username,
        exclude_credentials=exclude,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )
    challenge_token = store_challenge("register", admin_id, options.challenge)
    return challenge_token, json.loads(options_to_json(options))


def verify_registration(
    *,
    admin_id: int,
    challenge_token: str,
    credential: dict[str, Any],
    request_host: str | None = None,
    request_origin: str | None = None,
) -> dict[str, Any]:
    payload = pop_challenge(challenge_token, kind="register", admin_id=admin_id)
    if payload is None:
        raise ValueError("Invalid or expired WebAuthn registration challenge")
    verification = verify_registration_response(
        credential=credential,
        expected_challenge=payload["challenge"],
        expected_rp_id=resolve_rp_id(request_host),
        expected_origin=resolve_origin(request_origin),
    )
    return {
        "credential_id": bytes_to_base64url(verification.credential_id),
        "public_key": bytes_to_base64url(verification.credential_public_key),
        "sign_count": int(verification.sign_count),
        "aaguid": str(verification.aaguid) if verification.aaguid else None,
        "transports": credential.get("response", {}).get("transports"),
    }


def build_authentication_options(
    *,
    admin_id: int,
    credential_ids: list[str],
    request_host: str | None = None,
) -> tuple[str, dict[str, Any]]:
    allow = [PublicKeyCredentialDescriptor(id=base64url_to_bytes(cred_id)) for cred_id in credential_ids]
    options = generate_authentication_options(
        rp_id=resolve_rp_id(request_host),
        allow_credentials=allow,
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    challenge_token = store_challenge("authenticate", admin_id, options.challenge)
    return challenge_token, json.loads(options_to_json(options))


def verify_authentication(
    *,
    admin_id: int,
    challenge_token: str,
    credential: dict[str, Any],
    credential_id: str,
    public_key: str,
    sign_count: int,
    request_host: str | None = None,
    request_origin: str | None = None,
) -> int:
    payload = pop_challenge(challenge_token, kind="authenticate", admin_id=admin_id)
    if payload is None:
        raise ValueError("Invalid or expired WebAuthn authentication challenge")
    verification = verify_authentication_response(
        credential=credential,
        expected_challenge=payload["challenge"],
        expected_rp_id=resolve_rp_id(request_host),
        expected_origin=resolve_origin(request_origin),
        credential_public_key=base64url_to_bytes(public_key),
        credential_current_sign_count=sign_count,
    )
    return int(verification.new_sign_count)
