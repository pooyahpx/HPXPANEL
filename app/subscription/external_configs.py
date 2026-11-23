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


def collect_external_config_links(sub_settings) -> list[str]:
    """Enabled mother configs from settings + legacy EXTERNAL_CONFIG env."""
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
        if enabled is False:
            continue
        link = getattr(item, "link", None) or (item.get("link") if isinstance(item, dict) else None)
        name = getattr(item, "name", None) or (item.get("name") if isinstance(item, dict) else None)
        if link:
            _add(str(link), str(name) if name else None)

    env_link = (subscription_env_settings.external_config or "").strip()
    if env_link:
        _add(env_link)

    return links
