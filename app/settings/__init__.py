from aiocache import cached

from app.db import GetDB
from app.db.crud.settings import get_settings
from app.models import settings


@cached()
async def telegram_settings() -> settings.Telegram:
    async with GetDB() as db:
        db_settings = await get_settings(db)

    validated_settings = settings.Telegram.model_validate(db_settings.telegram)
    return validated_settings


@cached()
async def webhook_settings() -> settings.Webhook:
    async with GetDB() as db:
        db_settings = await get_settings(db)

    validated_settings = settings.Webhook.model_validate(db_settings.webhook)
    return validated_settings


@cached()
async def notification_settings() -> settings.NotificationSettings:
    async with GetDB() as db:
        db_settings = await get_settings(db)

    validated_settings = settings.NotificationSettings.model_validate(db_settings.notification_settings)
    return validated_settings


@cached()
async def notification_enable() -> settings.NotificationEnable:
    async with GetDB() as db:
        db_settings = await get_settings(db)

    validated_settings = settings.NotificationEnable.model_validate(db_settings.notification_enable)
    return validated_settings


@cached()
async def subscription_settings() -> settings.Subscription:
    async with GetDB() as db:
        db_settings = await get_settings(db)

    validated_settings = settings.Subscription.model_validate(db_settings.subscription)
    return validated_settings


@cached()
async def hwid_settings() -> settings.HWIDSettings:
    async with GetDB() as db:
        db_settings = await get_settings(db)

    validated_settings = settings.HWIDSettings.model_validate(db_settings.hwid)
    return validated_settings


@cached()
async def general_settings() -> settings.General:
    async with GetDB() as db:
        db_settings = await get_settings(db)

    validated_settings = settings.General.model_validate(db_settings.general)
    return validated_settings


async def refresh_caches() -> None:
    await telegram_settings.cache.clear()
    await webhook_settings.cache.clear()
    await notification_settings.cache.clear()
    await notification_enable.cache.clear()
    await subscription_settings.cache.clear()
    await hwid_settings.cache.clear()
    await general_settings.cache.clear()


async def handle_settings_message(data: dict):
    """Handle settings update message from NATS router."""
    action = data.get("action", "refresh")
    if action in ("refresh", None):
        await refresh_caches()
        try:
            from app.telegram import telegram_bot_manager
        except Exception:
            telegram_bot_manager = None
        else:
            await telegram_bot_manager.sync_from_settings()
    if action in ("refresh", "copilot_refresh", None):
        from config import refresh_copilot_settings

        refresh_copilot_settings()
