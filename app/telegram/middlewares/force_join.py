"""Block buyers who have not joined the shop's required channel (toggle per shop, OFF by default)."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.db.crud.shop import get_telegram_lang
from app.telegram.keyboards.shop import ForceJoinKeyboard
from app.telegram.utils.force_join import default_channel_url, force_join_required, is_channel_member
from app.telegram.utils.i18n import t
from app.telegram.utils.shop_helpers import get_buyer_shop_config

# CallbackData prefix for ShopAction.check_join (recheck button must reach its handler).
_CHECK_JOIN_PREFIX = "shop:chj"


def _is_exempt(event: TelegramObject, current_state: str | None) -> bool:
    if isinstance(event, CallbackQuery):
        return (event.data or "").startswith(_CHECK_JOIN_PREFIX)
    if isinstance(event, Message):
        text = (event.text or "").strip().lower()
        if text.startswith("/claimowner"):
            return True
        if current_state and current_state.startswith("ClaimOwner"):
            return True
    return False


def _start_arg(event: TelegramObject) -> str | None:
    if isinstance(event, Message) and event.text and event.text.startswith("/start"):
        parts = event.text.split(maxsplit=1)
        if len(parts) > 1:
            return parts[1].strip() or None
    return None


class ForceJoinMiddleware(BaseMiddleware):
    """
    Inner middleware for buyer-facing routers (needs ``admin`` / ``db`` from ACLMiddleware).

    Panel admins/owners always bypass. When the resolved shop has force-join ON and a channel set,
    non-members get the join prompt instead of the requested handler.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        admin = data.get("admin")
        db = data.get("db")
        user = getattr(event, "from_user", None)
        if admin is not None or db is None or user is None:
            return await handler(event, data)

        state = data.get("state")
        current_state = await state.get_state() if state is not None else None
        if _is_exempt(event, current_state):
            return await handler(event, data)

        config = await get_buyer_shop_config(
            db,
            state,
            telegram_id=user.id,
            start_arg=_start_arg(event),
            require_selection=False,
        )
        if not force_join_required(config):
            return await handler(event, data)

        bot = data.get("bot")
        if await is_channel_member(bot, str(config.force_join_channel_id).strip(), user.id):
            return await handler(event, data)

        lang = (await get_telegram_lang(db, user.id)) or "fa"
        url = (config.force_join_channel_url or "").strip() or default_channel_url(config.force_join_channel_id)
        text = t(lang, "force_join_prompt")
        markup = ForceJoinKeyboard(lang, url).as_markup()
        if isinstance(event, CallbackQuery):
            await event.answer()
            if event.message is not None:
                try:
                    await event.message.edit_text(text, reply_markup=markup)
                except TelegramBadRequest:
                    await event.message.answer(text, reply_markup=markup)
        elif isinstance(event, Message):
            await event.answer(text, reply_markup=markup)
        return None
