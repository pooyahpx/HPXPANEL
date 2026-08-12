from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, Update

from app.db import GetDB
from app.db.crud.admin import build_admin_details, get_admin_by_telegram_id
from app.db.models import AdminStatus
from app.models.settings import Telegram
from app.settings import telegram_settings
from app.utils.logger import get_logger

logger = get_logger("Telegram-bot")


async def _deny_access(event: Update, user_id: int, reason: str) -> None:
    logger.warning(f"Telegram access denied for {user_id}: {reason}")
    text = (
        "⛔ Access denied.\n\n"
        f"Your Telegram ID: <code>{user_id}</code>\n"
        "Add this ID in HPXPANEL → Admins → Telegram ID, then send /start again."
    )
    try:
        if event.message and isinstance(event.message, Message):
            await event.message.answer(text, parse_mode="HTML")
        elif event.callback_query and isinstance(event.callback_query, CallbackQuery):
            await event.callback_query.answer("Access denied — link your Telegram ID in the panel.", show_alert=True)
    except Exception as err:
        logger.debug(f"Failed to send access-denied reply: {err}")


class ACLMiddleware(BaseMiddleware):
    async def __call__(
        self, handler: Callable[[Update, dict[str, Any]], Awaitable[Any]], event: Update, data: dict[str, Any]
    ) -> Any:
        message_obj = event.message or event.callback_query or event.inline_query
        if message_obj is None or message_obj.from_user is None:
            return None
        user_id = message_obj.from_user.id
        async with GetDB() as db:
            settings: Telegram = await telegram_settings()
            admin = await get_admin_by_telegram_id(db, user_id)
            if admin:
                if admin.status == AdminStatus.disabled:
                    if settings.for_admins_only:
                        await _deny_access(event, user_id, "admin disabled")
                        return None
                    data["admin"] = None
                else:
                    admin = build_admin_details(admin, include_loaded_metrics=True)
                    data["admin"] = admin
            else:
                if settings.for_admins_only:
                    await _deny_access(event, user_id, "telegram_id not linked to any admin")
                    return None
                data["admin"] = None

            data["db"] = db
            return await handler(event, data)
