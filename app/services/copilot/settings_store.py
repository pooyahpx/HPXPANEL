from __future__ import annotations

import os

from copilot_env_store import copilot_env_path, mask_secret, update_copilot_env
import config
from config import CopilotSettings, refresh_copilot_settings


def build_copilot_env_patch(
    *,
    enabled: bool | None,
    provider: str | None,
    api_key: str | None,
    model: str | None,
    base_url: str | None,
    current: CopilotSettings | None = None,
) -> dict[str, str]:
    current = current or config.copilot_settings
    patch: dict[str, str] = {}

    if enabled is not None:
        patch["COPILOT_ENABLED"] = "true" if enabled else "false"
    if provider is not None:
        patch["COPILOT_PROVIDER"] = provider.strip().lower()
    if model is not None:
        patch["COPILOT_MODEL"] = model.strip()
    if base_url is not None:
        patch["COPILOT_BASE_URL"] = base_url.strip()

    if api_key is not None:
        key = api_key.strip()
        if key:
            patch["OPENAI_API_KEY"] = key

    effective_provider = patch.get("COPILOT_PROVIDER", current.provider)
    has_key = bool(patch.get("OPENAI_API_KEY") or current.api_key.strip())
    if effective_provider != "ollama" and not has_key and api_key is not None:
        raise ValueError("API key is required for this provider")

    return patch


def persist_copilot_settings(
    *,
    enabled: bool | None = None,
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> CopilotSettings:
    patch = build_copilot_env_patch(
        enabled=enabled,
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
        current=config.copilot_settings,
    )
    if not patch:
        return config.copilot_settings
    update_copilot_env(patch)
    return refresh_copilot_settings()


def masked_api_key(settings: CopilotSettings | None = None) -> str:
    settings = settings or config.copilot_settings
    return mask_secret(settings.api_key)


def copilot_env_is_writable() -> bool:
    path = copilot_env_path()
    if path.is_file():
        return os.access(path, os.W_OK)
    parent = path.parent
    return parent.exists() and os.access(parent, os.W_OK)
