import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud.settings import get_settings, modify_settings
from app.db.models import Settings
from app.models.settings import General, SettingsSchema, Subscription
from app.nats.message import MessageTopic
from app.nats.router import router
from app.notification.client import define_client
from app.settings import refresh_caches
from app.telegram import startup_telegram_bot

from . import BaseOperation

SUB_PAGE_FIELDS = (
    "sub_theme",
    "sub_theme_mode",
    "sub_show_install_guide",
    "sub_show_apps",
    "sub_show_usage_chart",
    "sub_show_config_share",
    "sub_allow_mode_toggle",
)
# Kept even when dashboard clients omit them from the PATCH body.
SUB_INTERNAL_FIELDS = ("last_notified_sub_origin",)


class SettingsOperation(BaseOperation):
    @staticmethod
    async def reset_services(old_settings: SettingsSchema, new_settings: SettingsSchema):
        if new_settings.telegram != old_settings.telegram:
            await startup_telegram_bot()
        # When webhooks are disabled, send_notifications() already returns early
        # Pending webhook notifications will be processed when webhooks are re-enabled
        if old_settings.notification_settings.proxy_url != new_settings.notification_settings.proxy_url:
            await define_client()

    async def get_settings(self, db: AsyncSession) -> Settings:
        return await get_settings(db)

    async def modify_settings(self, db: AsyncSession, modify: SettingsSchema) -> SettingsSchema:
        db_settings = await get_settings(db)
        old_settings = SettingsSchema.model_validate(db_settings)

        # Older clients (e.g. the subscriptions settings form) may omit the sub page appearance
        # fields; keep the stored values instead of silently resetting them to defaults.
        if modify.subscription and db_settings.subscription:
            stored_subscription = Subscription.model_validate(db_settings.subscription)
            # Always keep internal notify fingerprint; clients never send it.
            preserved = {
                field: getattr(stored_subscription, field)
                for field in (*SUB_PAGE_FIELDS, *SUB_INTERNAL_FIELDS)
                if field not in modify.subscription.model_fields_set or field in SUB_INTERNAL_FIELDS
            }
            if preserved:
                modify.subscription = modify.subscription.model_copy(update=preserved)

        old_url_prefix = ((old_settings.subscription.url_prefix if old_settings.subscription else None) or "").strip()
        old_panel_url = ((old_settings.telegram.panel_url if old_settings.telegram else None) or "").strip()

        if modify.general and modify.general.custom_variables is not None:
            subscription = modify.subscription or Subscription.model_validate(db_settings.subscription)
            modify.subscription = subscription.model_copy(update={"custom_variables": modify.general.custom_variables})
            modify.general = modify.general.model_copy(update={"custom_variables": None})

        db_settings = await modify_settings(db, db_settings, modify)
        new_settings = SettingsSchema.model_validate(db_settings)
        if new_settings.general and new_settings.subscription:
            new_settings.general.custom_variables = new_settings.subscription.custom_variables

        await refresh_caches()
        # Publish settings update via NATS (all workers will refresh their caches)
        await router.publish(MessageTopic.SETTING, {"action": "refresh"})
        asyncio.create_task(self.reset_services(old_settings, new_settings))

        new_url_prefix = ((new_settings.subscription.url_prefix if new_settings.subscription else None) or "").strip()
        new_panel_url = ((new_settings.telegram.panel_url if new_settings.telegram else None) or "").strip()
        if old_url_prefix != new_url_prefix or old_panel_url != new_panel_url:
            asyncio.create_task(_notify_buyers_domain_changed())

        return new_settings

    async def get_general_settings(self, db: AsyncSession):
        settings = await self.get_settings(db)
        general = General.model_validate(settings.general)
        subscription = Subscription.model_validate(settings.subscription)
        return general.model_copy(update={"custom_variables": subscription.custom_variables})


async def _notify_buyers_domain_changed() -> None:
    try:
        from app.telegram.utils.sub_delivery import notify_buyers_subscription_domain_change

        notified = await notify_buyers_subscription_domain_change(force=True)
        if notified:
            from app.utils.logger import get_logger

            get_logger("settings").info("Notified %s telegram buyers after subscription domain change", notified)
    except Exception:
        from app.utils.logger import get_logger

        get_logger("settings").exception("Failed to notify telegram buyers after domain change")
