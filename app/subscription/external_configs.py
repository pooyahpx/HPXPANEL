"""Mother / external share links injected into user subscriptions."""

from __future__ import annotations

from urllib.parse import quote

from config import subscription_env_settings

EXTERNAL_LINK_SCHEMES = (
    "vless://",
    "vmess://",
    "trojan://",
    "ss://",
    "ssr://",
    "hysteria://",
    "hysteria2://",
    "hy2://",
    "tuic://",
    "wireguard://",
    "wg://",
    "anytls://",
    "socks://",
    "socks5://",
    "http://",
    "https://",
)


def is_share_link(value: str) -> bool:
    lowered = (value or "").strip().lower()
    return any(lowered.startswith(prefix) for prefix in EXTERNAL_LINK_SCHEMES)


def normalize_external_link(link: str, name: str | None = None) -> str:
    """Return a share link, optionally overriding the #remark fragment."""
    cleaned = (link or "").strip()
    if not cleaned:
        return ""
    label = (name or "").strip()
    if not label:
        return cleaned
    base = cleaned.rsplit("#", 1)[0]
    return f"{base}#{quote(label)}"


def _status_value(user) -> str:
    status = getattr(user, "status", None)
    if status is None:
        return ""
    return status.value if hasattr(status, "value") else str(status)


def user_has_remaining_quota(user) -> bool:
    """True when the user still has volume left on this panel (or is unlimited)."""
    data_limit = getattr(user, "data_limit", None)
    if data_limit is None or int(data_limit) <= 0:
        return True
    used = int(getattr(user, "used_traffic", 0) or 0)
    return used < int(data_limit)


def user_may_receive_external_configs(user, *, respect_quota: bool = True) -> bool:
    """Gate mother configs by local user status + remaining volume."""
    if _status_value(user) not in {"active", "on_hold"}:
        return False
    if not respect_quota:
        return True
    return user_has_remaining_quota(user)


def _item_respects_quota(item) -> bool:
    if isinstance(item, dict):
        return bool(item.get("respect_user_quota", True))
    return bool(getattr(item, "respect_user_quota", True))


def collect_external_config_links(sub_settings, user=None) -> list[str]:
    """Enabled mother configs from settings + legacy EXTERNAL_CONFIG env.

    When ``user`` is provided, configs with ``respect_user_quota`` (default True)
    are only included while that user is active/on_hold and still has remaining
    volume on this panel — so a shared remote UUID is not offered to exhausted
    accounts.
    """
    links: list[str] = []
    seen: set[str] = set()

    def _add(raw: str, name: str | None = None) -> None:
        normalized = normalize_external_link(raw, name)
        if not normalized or not is_share_link(normalized):
            return
        key = normalized.rsplit("#", 1)[0]
        if key in seen:
            return
        seen.add(key)
        links.append(normalized)

    for item in getattr(sub_settings, "external_configs", None) or []:
        enabled = getattr(item, "enabled", True)
        if isinstance(item, dict):
            enabled = item.get("enabled", True)
        if enabled is False:
            continue
        if user is not None and not user_may_receive_external_configs(
            user, respect_quota=_item_respects_quota(item)
        ):
            continue
        link = getattr(item, "link", None) or (item.get("link") if isinstance(item, dict) else None)
        name = getattr(item, "name", None) or (item.get("name") if isinstance(item, dict) else None)
        if link:
            _add(str(link), str(name) if name else None)

    # Legacy env link always respects user quota when a user is in context.
    env_link = (subscription_env_settings.external_config or "").strip()
    if env_link and (user is None or user_may_receive_external_configs(user, respect_quota=True)):
        _add(env_link)

    return links
