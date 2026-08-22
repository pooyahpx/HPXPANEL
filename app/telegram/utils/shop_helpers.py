"""Shared helpers for Telegram shop payment + support."""

from __future__ import annotations

from aiogram import Bot
from aiogram.types import Message, User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud.admin import list_admins_with_telegram
from app.db.crud.shop import get_owner_admin, get_telegram_lang, has_test_claimed, mark_join_notified
from app.db.models import ShopConfig
from app.models.admin import AdminDetails
from app.telegram.utils.i18n import rich, t

MAX_SHOP_CARDS = 3


def shop_cards(config: ShopConfig | None) -> list[dict[str, str]]:
    if not config:
        return []
    if config.cards:
        return [{"number": c.get("number", ""), "holder": c.get("holder", "")} for c in config.cards if c.get("number")]
    if config.card_number:
        return [{"number": config.card_number, "holder": config.card_holder or ""}]
    return []


def cards_summary(config: ShopConfig | None, lang: str) -> str:
    cards = shop_cards(config)
    if not cards:
        return "—"
    if len(cards) == 1:
        card = cards[0]
        return f"{card['number']} ({card['holder'] or '—'})"
    return t(lang, "admin_cards_count", count=len(cards))


def test_config_summary(config: ShopConfig | None, lang: str) -> str:
    if not config or not config.test_enabled:
        return t(lang, "no")
    from app.telegram.utils.i18n import format_bytes

    days = t(lang, "days_unlimited") if not config.test_expire_days else str(config.test_expire_days)
    groups = ",".join(str(g) for g in (config.test_group_ids or [])) or "—"
    return rich(
        lang,
        "admin_test_summary",
        data=format_bytes(config.test_data_limit),
        days=days,
        groups=groups,
    )


_DIGIT_TRANSLATE = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_group_ids(raw) -> list[int]:
    """Accept JSON lists, comma strings, and Persian digits; return unique int IDs."""
    if not raw:
        return []
    items: list = []
    if isinstance(raw, (list, tuple, set)):
        items = list(raw)
    elif isinstance(raw, str):
        items = [part.strip() for part in raw.replace(";", ",").split(",") if part.strip()]
    else:
        items = [raw]
    ids: list[int] = []
    seen: set[int] = set()
    for item in items:
        if isinstance(item, bool) or item is None:
            continue
        text = str(item).strip().translate(_DIGIT_TRANSLATE)
        try:
            group_id = int(text)
        except ValueError:
            continue
        if group_id > 0 and group_id not in seen:
            seen.add(group_id)
            ids.append(group_id)
    return ids


def safe_error_text(exc: BaseException, limit: int = 180) -> str:
    return str(exc).replace("{", "(").replace("}", ")")[:limit]


async def format_groups_hint(db: AsyncSession) -> str:
    from app.db.crud.group import get_groups_simple
    from app.models.group import GroupSimpleListQuery

    rows, _ = await get_groups_simple(db, GroupSimpleListQuery(all=True, limit=50))
    if not rows:
        return "—"
    return "\n".join(f"{gid}: {str(name).replace('{', '(').replace('}', ')')}" for gid, name in rows[:30])


async def buyer_show_test_button(db: AsyncSession, telegram_id: int, config: ShopConfig | None) -> bool:
    if not config or not config.test_enabled:
        return False
    if not normalize_group_ids(config.test_group_ids):
        return False
    return not await has_test_claimed(db, telegram_id)


def welcome_note_preview(note: str | None, lang: str) -> str:
    if not note:
        return t(lang, "welcome_default_hint")
    preview = note.replace("\n", " ")[:40]
    return preview + ("…" if len(note) > 40 else "")


def shop_home_text(lang: str, config: ShopConfig | None) -> str:
    if config and config.welcome_note:
        return config.welcome_note
    return rich(lang, "shop_home")


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
    cards = shop_cards(config)
    if not cards:
        text = t(lang, "pay_no_card")
    elif len(cards) == 1:
        card = cards[0]
        text = rich(
            lang,
            "pay_card",
            card=card["number"],
            holder=card["holder"] or "—",
        )
    else:
        lines = [t(lang, "pay_cards_header")]
        for index, card in enumerate(cards, start=1):
            lines.append(
                rich(
                    lang,
                    "pay_card_item",
                    index=index,
                    card=card["number"],
                    holder=card["holder"] or "—",
                )
            )
        lines.append(t(lang, "pay_cards_footer"))
        text = "\n".join(lines)
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
    allow_reply: bool = True,
) -> None:
    from app.telegram.keyboards.shop import SupportReplyKeyboard

    header = rich(
        admin_lang,
        "support_from_user",
        buyer=buyer_label,
        id=buyer_telegram_id,
    )
    markup = SupportReplyKeyboard(admin_lang, buyer_telegram_id).as_markup() if allow_reply else None
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


async def notify_all_admins_support(
    db: AsyncSession,
    *,
    bot: Bot,
    buyer_telegram_id: int,
    buyer_label: str,
    message: Message,
) -> None:
    """Forward a buyer support message to every panel admin linked to Telegram."""
    from app.db.crud.shop import get_support_ticket

    ticket = await get_support_ticket(db, buyer_telegram_id)
    allow_reply = ticket is not None and ticket.status == "open" and ticket.handler_admin_id is None
    notified_ids: set[int] = set()
    for panel_admin in await list_admins_with_telegram(db):
        chat_id = panel_admin.telegram_id
        if chat_id is None or chat_id in notified_ids or chat_id == buyer_telegram_id:
            continue
        admin_lang = (await get_telegram_lang(db, chat_id)) or "fa"
        try:
            await notify_shop_admin_support(
                bot=bot,
                admin_telegram_id=chat_id,
                admin_lang=admin_lang,
                buyer_telegram_id=buyer_telegram_id,
                buyer_label=buyer_label,
                message=message,
                allow_reply=allow_reply,
            )
            notified_ids.add(chat_id)
        except Exception:
            pass


async def notify_all_admins_order(
    db: AsyncSession,
    *,
    bot: Bot,
    buyer_telegram_id: int,
    shop_admin_id: int,
    order_id: int,
    buyer_label: str,
    plan_name: str,
    price: str,
    file_id: str,
    reply_markup_factory,
) -> None:
    """Notify every linked panel admin about a new shop order."""
    notified_ids: set[int] = set()
    for panel_admin in await list_admins_with_telegram(db):
        chat_id = panel_admin.telegram_id
        if chat_id is None or chat_id in notified_ids or chat_id == buyer_telegram_id:
            continue
        admin_lang = (await get_telegram_lang(db, chat_id)) or "fa"
        caption = t(
            admin_lang,
            "admin_new_order",
            id=order_id,
            buyer=buyer_label,
            plan=plan_name,
            price=price,
        )
        markup = reply_markup_factory(admin_lang) if panel_admin.id == shop_admin_id else None
        try:
            await bot.send_photo(
                chat_id=chat_id,
                photo=file_id,
                caption=caption,
                reply_markup=markup,
            )
            notified_ids.add(chat_id)
        except Exception:
            pass


def _buyer_label(user: TgUser) -> tuple[str, str]:
    name = (user.full_name or "").strip() or "—"
    username = f"@{user.username}" if user.username else "—"
    return name, username


async def notify_admins_user_joined(db: AsyncSession, bot: Bot | None, user: TgUser) -> None:
    if bot is None:
        return
    if not await mark_join_notified(db, user.id):
        return

    name, username = _buyer_label(user)
    notified_ids: set[int] = set()
    for panel_admin in await list_admins_with_telegram(db):
        chat_id = panel_admin.telegram_id
        if chat_id is None or chat_id in notified_ids or chat_id == user.id:
            continue
        admin_lang = (await get_telegram_lang(db, chat_id)) or "fa"
        text = rich(
            admin_lang,
            "admin_user_joined",
            name=name,
            username=username,
            id=user.id,
        )
        try:
            await bot.send_message(chat_id, text)
            notified_ids.add(chat_id)
        except Exception:
            pass


async def notify_owner_order_approved(
    *,
    db: AsyncSession,
    bot: Bot | None,
    approver: AdminDetails,
    order_id: int,
    buyer_label: str,
    plan_name: str,
    username: str,
) -> None:
    if bot is None or approver.is_owner:
        return
    owner = await get_owner_admin(db)
    if owner is None or not owner.telegram_id or owner.telegram_id == approver.telegram_id:
        return
    owner_lang = (await get_telegram_lang(db, owner.telegram_id)) or "fa"
    text = rich(
        owner_lang,
        "admin_order_approved_by_other",
        id=order_id,
        admin=approver.username,
        buyer=buyer_label,
        plan=plan_name,
        username=username,
    )
    try:
        await bot.send_message(owner.telegram_id, text)
    except Exception:
        pass


async def notify_admins_support_claimed(
    db: AsyncSession,
    *,
    bot: Bot | None,
    buyer_telegram_id: int,
    handler: AdminDetails,
) -> None:
    if bot is None:
        return
    notified_ids: set[int] = set()
    for panel_admin in await list_admins_with_telegram(db):
        chat_id = panel_admin.telegram_id
        if chat_id is None or chat_id in notified_ids or chat_id == buyer_telegram_id:
            continue
        if panel_admin.id == handler.id:
            continue
        admin_lang = (await get_telegram_lang(db, chat_id)) or "fa"
        text = rich(
            admin_lang,
            "support_claimed_by_other",
            admin=handler.username,
            id=buyer_telegram_id,
        )
        try:
            await bot.send_message(chat_id, text)
            notified_ids.add(chat_id)
        except Exception:
            pass


async def notify_admins_support_closed(
    db: AsyncSession,
    *,
    bot: Bot | None,
    buyer_telegram_id: int,
    handler: AdminDetails,
) -> None:
    if bot is None:
        return
    notified_ids: set[int] = set()
    for panel_admin in await list_admins_with_telegram(db):
        chat_id = panel_admin.telegram_id
        if chat_id is None or chat_id in notified_ids or chat_id == buyer_telegram_id:
            continue
        if panel_admin.id == handler.id:
            continue
        admin_lang = (await get_telegram_lang(db, chat_id)) or "fa"
        text = rich(
            admin_lang,
            "support_closed_by_other",
            admin=handler.username,
            id=buyer_telegram_id,
        )
        try:
            await bot.send_message(chat_id, text)
            notified_ids.add(chat_id)
        except Exception:
            pass


async def notify_owner_user_created(
    *,
    db: AsyncSession,
    bot: Bot | None,
    creator: AdminDetails,
    username: str,
    groups: str,
    data_limit: int | None,
    expire,
) -> None:
    if bot is None or creator.is_owner:
        return
    owner = await get_owner_admin(db)
    if owner is None or not owner.telegram_id:
        return
    from app.telegram.utils.i18n import format_bytes, t

    owner_lang = (await get_telegram_lang(db, owner.telegram_id)) or "fa"
    data_str = format_bytes(data_limit) if data_limit else t(owner_lang, "limit_unlimited")
    if expire:
        expire_str = expire.strftime("%Y-%m-%d %H:%M")
    else:
        expire_str = t(owner_lang, "days_unlimited")
    text = rich(
        owner_lang,
        "owner_log_user_created",
        admin=creator.username,
        username=username,
        groups=groups or "—",
        data=data_str,
        expire=expire_str,
    )
    try:
        await bot.send_message(owner.telegram_id, text)
    except Exception:
        pass
