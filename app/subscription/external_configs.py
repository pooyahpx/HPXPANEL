"""Mother / external share links injected into user subscriptions."""

from __future__ import annotations

from urllib.parse import quote

from config import subscription_env_settings

from app.subscription.mother_personalize import personalize_share_link

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
    # vmess payloads embed the remark — leave them alone here
    if cleaned.lower().startswith("vmess://"):
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


def _item_flag(item, key: str, default: bool = True) -> bool:
    if isinstance(item, dict):
        return bool(item.get(key, default))
    return bool(getattr(item, key, default))


def _item_respects_quota(item) -> bool:
    # Shared (non-personalized) mother links must always respect local volume,
    # otherwise exhausted users keep a freeloader UUID forever.
    if not _item_flag(item, "personalize", False):
        return True
    return _item_flag(item, "respect_user_quota", True)


def collect_external_config_links(sub_settings, user=None) -> list[str]:
    """Enabled mother configs from settings + legacy EXTERNAL_CONFIG env.

    When ``user`` is provided:
    - configs with ``respect_user_quota`` (default True) are only included while
      that user is active/on_hold and still has remaining volume on this panel
    - configs with ``personalize`` (default False) rewrite UUID/password to the
      local user's credentials — only enable when mother is a Node / same clients
    """
    links: list[str] = []
    seen: set[str] = set()

    def _add(raw: str, name: str | None = None, *, personalize: bool = False) -> None:
        candidate = (raw or "").strip()
        if not candidate:
            return
        if user is not None and personalize:
            candidate = personalize_share_link(candidate, user, name=name)
        else:
            candidate = normalize_external_link(candidate, name)
        if not candidate or not is_share_link(candidate):
            return
        key = candidate.rsplit("#", 1)[0]
        if key in seen:
            return
        seen.add(key)
        links.append(candidate)

    for item in getattr(sub_settings, "external_configs", None) or []:
        enabled = _item_flag(item, "enabled", True)
        if enabled is False:
            continue
        if user is not None and not user_may_receive_external_configs(
            user, respect_quota=_item_respects_quota(item)
        ):
            continue
        link = getattr(item, "link", None) or (item.get("link") if isinstance(item, dict) else None)
        name = getattr(item, "name", None) or (item.get("name") if isinstance(item, dict) else None)
        personalize = _item_flag(item, "personalize", False)
        if link:
            _add(str(link), str(name) if name else None, personalize=personalize)

    # Legacy env link always respects user quota; never personalize (shared UUID).
    env_link = (subscription_env_settings.external_config or "").strip()
    if env_link and (user is None or user_may_receive_external_configs(user, respect_quota=True)):
        _add(env_link, personalize=False)

    return links
