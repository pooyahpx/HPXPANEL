from datetime import UTC, datetime as dt, timedelta as td

from app import scheduler
from app.db import GetDB
from app.db.crud.hpx_pulse import get_hpx_pulses, update_hpx_pulse
from app.db.models import HpxPulseStatus
from app.utils.logger import get_logger
from config import runtime_settings

logger = get_logger("hpx-pulse-auto-restart")


async def hpx_pulse_auto_restart_job():
    try:
        async with GetDB() as db:
            pulses, _ = await get_hpx_pulses(db, offset=0, limit=500)
            now = dt.now(UTC)
            for pulse in pulses:
                interval = pulse.auto_restart_interval_minutes
                if not pulse.enabled or not interval or interval < 1:
                    continue
                if pulse.status in {HpxPulseStatus.stopped, HpxPulseStatus.stopping, HpxPulseStatus.pending_claim}:
                    continue
                if not pulse.iran_agent_key_hash and not pulse.abroad_agent_key_hash:
                    continue

                last = pulse.last_auto_restart_at
                if last is not None:
                    if last.tzinfo is None:
                        last = last.replace(tzinfo=UTC)
                    if now - last < td(minutes=interval):
                        continue

                update: dict = {
                    "last_auto_restart_at": now,
                    "last_status_change": now,
                    "message": f"Auto-restart queued (every {interval} min)",
                }
                if pulse.iran_agent_key_hash:
                    update["iran_agent_command"] = "restart"
                if pulse.abroad_agent_key_hash:
                    update["abroad_agent_command"] = "restart"

                await update_hpx_pulse(db, pulse, update)
                logger.info("Queued auto-restart for pulse %s (every %s min)", pulse.name, interval)

            await db.commit()
    except Exception:
        logger.exception("hpx_pulse_auto_restart_job failed")


if runtime_settings.role.runs_scheduler:
    now = dt.now(UTC)
    scheduler.add_job(
        hpx_pulse_auto_restart_job,
        "interval",
        seconds=60,
        coalesce=True,
        max_instances=1,
        start_date=now + td(seconds=45),
        id="hpx_pulse_auto_restart",
        replace_existing=True,
    )
