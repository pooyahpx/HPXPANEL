"""Shared helpers for Telegram shop payment + support."""

from __future__ import annotations

from aiogram import Bot
from aiogram.types import Message

from app.db.models import ShopConfig
from app.telegram.utils.i18n import rich, t


def card_note_preview(note: str | None, lang: str) -> str:
    if not note:
        return "—"
    preview = note.replace("\n", " ")[:40]
    return preview + ("…" if len(note) > 40 else "")


def card_photos_count(config: ShopConfig | None) -> int:
    if not config or not config.card_photos:
        return 0
    return len(config.card_photos)


def parse_optional_limit(raw: str) -> int | None:
    value = raw.strip().lower()
    if value in ("", "-", "none", "نامحدود", "unlimited"):
        return None
    limit = int(value.replace(",", "").replace("٬", ""))
    if limit < 0:
        raise ValueError("negative limit")
    return limit


def build_pay_card_section(lang: str, config: ShopConfig) -> str:
    if config.card_number:
        text = rich(
            lang,
            "pay_card",
            card=config.card_number,
            holder=config.card_holder or "—",
        )
    else:
        text = t(lang, "pay_no_card")
    if config.card_note:
        text += f"\n\n{config.card_note}"
    return text


async def send_card_photos(bot: Bot, chat_id: int, config: ShopConfig) -> None:
    photos = list(config.card_photos or [])
    for file_id in photos:
        try:
            await bot.send_photo(chat_id, photo=file_id)
        except Exception:
            pass


async def notify_shop_admin_support(
    *,
    bot: Bot,
    admin_telegram_id: int,
    admin_lang: str,
    buyer_telegram_id: int,
    buyer_label: str,
    message: Message,
) -> None:
    from app.telegram.keyboards.shop import SupportReplyKeyboard

    header = rich(
        admin_lang,
        "support_from_user",
        buyer=buyer_label,
        id=buyer_telegram_id,
    )
    markup = SupportReplyKeyboard(admin_lang, buyer_telegram_id).as_markup()
    if message.photo:
        caption = header
        if message.caption:
            caption += f"\n\n{message.caption}"
        await bot.send_photo(
            chat_id=admin_telegram_id,
            photo=message.photo[-1].file_id,
            caption=caption,
            reply_markup=markup,
        )
    elif message.text:
        await bot.send_message(
            chat_id=admin_telegram_id,
            text=f"{header}\n\n{message.text}",
            reply_markup=markup,
        )
    else:
        await bot.send_message(chat_id=admin_telegram_id, text=header, reply_markup=markup)
