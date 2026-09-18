"""Panel-side Pulse health watchdog, heal, and path failover/failback."""

from datetime import UTC, datetime as dt, timedelta as td

from app import scheduler
from app.db import GetDB
from app.db.crud.hpx_pulse import get_hpx_pulse_by_id, get_hpx_pulses, update_hpx_pulse
from app.db.models import HpxPulse, HpxPulseStatus
from app.services.hpx_pulse.healer import evaluate_and_repair
from app.utils.logger import get_logger
from config import runtime_settings

logger = get_logger("hpx-pulse-health")

FAILOVER_COOLDOWN = td(minutes=3)
FAILBACK_COOLDOWN = td(minutes=5)


async def _notify_pulse(title: str, detail: str | None = None) -> None:
    try:
        from app.db.crud.shop import get_owner_admin
        from app.telegram import get_bot

        bot = get_bot()
        if bot is None:
            return
        async with GetDB() as db:
            owner = await get_owner_admin(db)
            if owner is None or not owner.telegram_id:
                return
            text = f"⚠️ HPX Pulse <b>{title}</b>"
            if detail:
                text += f"\n{detail}"
            await bot.send_message(owner.telegram_id, text, parse_mode="HTML")
    except Exception:
        logger.debug("Could not send HPX Pulse alert", exc_info=True)


def _aware(value: dt | None) -> dt | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _agents_fresh(pulse: HpxPulse) -> bool:
    from app.services.hpx_pulse.healer import AGENT_STALE_SECONDS, _agent_stale

    if not pulse.iran_agent_key_hash or not pulse.abroad_agent_key_hash:
        return False
    return not _agent_stale(pulse.iran_agent_last_seen, threshold=AGENT_STALE_SECONDS) and not _agent_stale(
        pulse.abroad_agent_last_seen, threshold=AGENT_STALE_SECONDS
    )


async def _attempt_failover(db, primary: HpxPulse) -> bool:
    if not primary.auto_failover or not primary.backup_pulse_id:
        return False
    if primary.failover_active:
        return False
    last = _aware(primary.last_failover_at)
    if last and dt.now(UTC) - last < FAILOVER_COOLDOWN:
        return False

    backup = await get_hpx_pulse_by_id(db, primary.backup_pulse_id)
    if backup is None or backup.id == primary.id or not backup.enabled:
        return False

    now = dt.now(UTC)
    reason = primary.message or "primary unhealthy"

    # Pause primary agents.
    if primary.iran_agent_key_hash:
        primary.iran_agent_command = "stop"
    if primary.abroad_agent_key_hash:
        primary.abroad_agent_command = "stop"
    primary.failover_active = True
    primary.status = HpxPulseStatus.unhealthy
    primary.message = f"Failed over to backup pulse #{backup.id}: {reason}"
    primary.last_failover_at = now
    primary.last_status_change = now
    await update_hpx_pulse(
        db,
        primary,
        {
            "iran_agent_command": primary.iran_agent_command,
            "abroad_agent_command": primary.abroad_agent_command,
            "failover_active": True,
            "status": primary.status,
            "message": primary.message,
            "last_failover_at": now,
            "last_status_change": now,
        },
    )

    # Activate backup.
    if backup.iran_agent_key_hash:
        backup.iran_agent_command = "restart"
    if backup.abroad_agent_key_hash:
        backup.abroad_agent_command = "restart"
    backup.message = f"Activated as failover for {primary.name}"
    backup.last_status_change = now
    if backup.status in {HpxPulseStatus.stopped, HpxPulseStatus.error}:
        backup.status = HpxPulseStatus.starting
    await update_hpx_pulse(
        db,
        backup,
        {
            "iran_agent_command": backup.iran_agent_command,
            "abroad_agent_command": backup.abroad_agent_command,
            "message": backup.message,
            "last_status_change": now,
            "status": backup.status,
            "enabled": True,
        },
    )

    await _notify_pulse(
        primary.name,
        f"Switched to backup <b>{backup.name}</b>\nReason: {reason}",
    )
    logger.warning("Pulse failover: %s → %s (%s)", primary.name, backup.name, reason)
    return True


async def _attempt_failback(db, primary: HpxPulse) -> bool:
    if not primary.auto_failback or not primary.failover_active:
        return False
    if not primary.backup_pulse_id:
        return False
    last = _aware(primary.last_failover_at)
    if last and dt.now(UTC) - last < FAILBACK_COOLDOWN:
        return False
    if not _agents_fresh(primary):
        return False
    if primary.status == HpxPulseStatus.unhealthy and "Failed over" in (primary.message or ""):
        # Still marked unhealthy from failover message — require fresh heartbeats only.
        pass
    elif primary.status in {HpxPulseStatus.error, HpxPulseStatus.stopped}:
        return False

    backup = await get_hpx_pulse_by_id(db, primary.backup_pulse_id)
    now = dt.now(UTC)

    if primary.iran_agent_key_hash:
        primary.iran_agent_command = "restart"
    if primary.abroad_agent_key_hash:
        primary.abroad_agent_command = "restart"
    primary.failover_active = False
    primary.status = HpxPulseStatus.running
    primary.message = "Failback complete — primary path restored"
    primary.last_failover_at = now
    primary.last_status_change = now
    await update_hpx_pulse(
        db,
        primary,
        {
            "iran_agent_command": primary.iran_agent_command,
            "abroad_agent_command": primary.abroad_agent_command,
            "failover_active": False,
            "status": primary.status,
            "message": primary.message,
            "last_failover_at": now,
            "last_status_change": now,
        },
    )

    if backup is not None:
        if backup.iran_agent_key_hash:
            backup.iran_agent_command = "stop"
        if backup.abroad_agent_key_hash:
            backup.abroad_agent_command = "stop"
        backup.message = f"Standby after failback from {primary.name}"
        backup.last_status_change = now
        await update_hpx_pulse(
            db,
            backup,
            {
                "iran_agent_command": backup.iran_agent_command,
                "abroad_agent_command": backup.abroad_agent_command,
                "message": backup.message,
                "last_status_change": now,
            },
        )

    await _notify_pulse(primary.name, "Failback complete — primary path is healthy again")
    logger.info("Pulse failback: %s restored", primary.name)
    return True


async def hpx_pulse_health_job():
    try:
        async with GetDB() as db:
            pulses, _ = await get_hpx_pulses(db, offset=0, limit=500)
            for pulse in pulses:
                if not pulse.enabled:
                    continue
                if pulse.status in {HpxPulseStatus.stopped, HpxPulseStatus.stopping, HpxPulseStatus.pending_claim}:
                    continue

                previous = pulse.status
                heal = evaluate_and_repair(pulse, auto=True)
                await update_hpx_pulse(
                    db,
                    pulse,
                    {
                        "status": pulse.status,
                        "message": pulse.message,
                        "last_status_change": pulse.last_status_change,
                        "last_health_check": pulse.last_health_check,
                        "last_heal_at": pulse.last_heal_at,
                        "last_heal_action": pulse.last_heal_action,
                        "heal_count_window": pulse.heal_count_window,
                        "iran_agent_command": pulse.iran_agent_command,
                        "abroad_agent_command": pulse.abroad_agent_command,
                    },
                )

                if heal.marked_unhealthy and previous != HpxPulseStatus.unhealthy:
                    await _notify_pulse(pulse.name, pulse.message)

                if pulse.status == HpxPulseStatus.unhealthy and not pulse.failover_active:
                    await _attempt_failover(db, pulse)
                elif pulse.failover_active:
                    await _attempt_failback(db, pulse)

            await db.commit()
    except Exception:
        logger.exception("hpx_pulse_health_job failed")


if runtime_settings.role.runs_scheduler:
    now = dt.now(UTC)
    scheduler.add_job(
        hpx_pulse_health_job,
        "interval",
        seconds=60,
        coalesce=True,
        max_instances=1,
        start_date=now + td(seconds=35),
        id="hpx_pulse_health",
        replace_existing=True,
    )
