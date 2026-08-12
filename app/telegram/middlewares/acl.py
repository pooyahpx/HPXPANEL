from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Update

from app.db import GetDB
from app.db.crud.admin import build_admin_details, get_admin_by_telegram_id
from app.db.models import AdminStatus


class ACLMiddleware(BaseMiddleware):
    """Resolve admin identity for updates. Non-admins always pass (shop buyers)."""

    async def __call__(
        self, handler: Callable[[Update, dict[str, Any]], Awaitable[Any]], event: Update, data: dict[str, Any]
    ) -> Any:
        message_obj = event.message or event.callback_query or event.inline_query
        if message_obj is None or message_obj.from_user is None:
            return None
        user_id = message_obj.from_user.id
        async with GetDB() as db:
            admin = await get_admin_by_telegram_id(db, user_id)
            if admin and admin.status != AdminStatus.disabled:
                data["admin"] = build_admin_details(admin, include_loaded_metrics=True)
            else:
                data["admin"] = None
            data["db"] = db
            return await handler(event, data)
