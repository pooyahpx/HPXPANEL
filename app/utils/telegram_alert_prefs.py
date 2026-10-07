"""Runtime Telegram alert toggles (owner-controlled via bot)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud.settings import get_settings
from app.models.settings import General
from app.settings import general_settings, refresh_caches


async def tunnel_alerts_enabled() -> bool:
    try:
        general = await general_settings()
        return bool(getattr(general, "telegram_tunnel_alerts", True))
    except Exception:
        return True


async def cpu_alerts_enabled() -> bool:
    try:
        general = await general_settings()
        return bool(getattr(general, "telegram_cpu_alerts", True))
    except Exception:
        return True


async def set_alert_prefs(
    db: AsyncSession,
    *,
    telegram_tunnel_alerts: bool | None = None,
    telegram_cpu_alerts: bool | None = None,
) -> General:
    db_settings = await get_settings(db)
    general = dict(db_settings.general or {})
    if telegram_tunnel_alerts is not None:
        general["telegram_tunnel_alerts"] = bool(telegram_tunnel_alerts)
    if telegram_cpu_alerts is not None:
        general["telegram_cpu_alerts"] = bool(telegram_cpu_alerts)
    db_settings.general = general
    await db.commit()
    await db.refresh(db_settings)
    await refresh_caches()
    return General.model_validate(db_settings.general or {})
