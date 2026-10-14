"""Forced channel-join gate helpers for the Telegram shop bot."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

JOINED_STATUSES = frozenset({"creator", "administrator", "member", "restricted"})

_USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{3,31}$")
_NUMERIC_RE = re.compile(r"^-100\d{5,}$")
_DIGIT_TRANSLATE = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_channel_id(raw: str | None) -> str | None:
    """Accept ``@name``, ``name``, ``https://t.me/name`` or ``-100123...``; return canonical id or None."""
    text = (raw or "").strip().translate(_DIGIT_TRANSLATE)
    if not text:
        return None
    lowered = text.lower()
    for prefix in ("https://t.me/", "http://t.me/", "t.me/", "https://telegram.me/", "telegram.me/"):
        if lowered.startswith(prefix):
            text = text[len(prefix) :].split("?")[0].strip("/")
            if text.startswith("+") or text.lower().startswith("joinchat"):
                return None  # invite links cannot be resolved to a chat id
            break
    if _NUMERIC_RE.match(text):
        return text
    name = text.removeprefix("@")
    if _USERNAME_RE.match(name):
        return f"@{name}"
    return None


def default_channel_url(channel_id: str | None) -> str | None:
    """Public t.me link for an ``@username`` channel; numeric ids have no derivable link."""
    if channel_id and channel_id.startswith("@"):
        return f"https://t.me/{channel_id[1:]}"
    return None


def is_joined_status(status: Any, is_member: bool | None = None) -> bool:
    """True when a ChatMember status counts as having joined the channel."""
    value = str(getattr(status, "value", status) or "").lower()
    if value not in JOINED_STATUSES:
        return False
    return not (value == "restricted" and is_member is False)


def force_join_required(config: Any) -> bool:
    """Gate applies only when the shop is enabled, the toggle is ON and a channel is configured."""
    return bool(
        config is not None
        and getattr(config, "enabled", False)
        and getattr(config, "force_join_enabled", False)
        and (getattr(config, "force_join_channel_id", None) or "").strip()
    )


async def is_channel_member(bot: Any, channel_id: str, user_id: int) -> bool:
    """
    Ask Telegram whether ``user_id`` is in ``channel_id``.

    Fails OPEN on API errors (bot not admin in channel, bad channel id, network): a broken
    configuration must not lock every buyer out of the shop.
    """
    if bot is None:
        return True
    chat: Any = int(channel_id) if re.fullmatch(r"-?\d+", channel_id) else channel_id
    try:
        member = await bot.get_chat_member(chat, user_id)
    except Exception as exc:
        logger.warning("force-join check failed for channel %s: %s", channel_id, exc)
        return True
    return is_joined_status(getattr(member, "status", None), getattr(member, "is_member", None))


async def user_passes_force_join(bot: Any, config: Any, user_id: int) -> bool:
    """Full gate decision for a buyer (toggle OFF / not configured → always passes)."""
    if not force_join_required(config):
        return True
    return await is_channel_member(bot, str(config.force_join_channel_id).strip(), int(user_id))
