from app import scheduler
from app.db import GetDB
from app.db.crud.observability import has_recent_alert, record_alert_event
from app.db.crud.shop import get_owner_admin
from app.operation import OperatorType
from app.operation.observability import ObservabilityOperation
from app.utils.logger import get_logger
from config import observability_settings, runtime_settings

logger = get_logger("observability-alerts")
observability_operator = ObservabilityOperation(operator_type=OperatorType.SYSTEM)


async def _notify_owner(message: str) -> None:
    try:
        from app.telegram import get_bot

        bot = get_bot()
        if bot is None:
            return
        async with GetDB() as db:
            owner = await get_owner_admin(db)
            if owner is None or not owner.telegram_id:
                return
            await bot.send_message(owner.telegram_id, message, parse_mode="HTML")
    except Exception:
        logger.debug("Could not send observability alert to owner", exc_info=True)


async def _maybe_alert(
    db,
    *,
    scope: str,
    metric: str,
    value: float,
    threshold: float,
    message: str,
    node_id: int | None = None,
) -> None:
    if await has_recent_alert(
        db,
        scope=scope,
        metric=metric,
        node_id=node_id,
        minutes=observability_settings.alert_cooldown_minutes,
    ):
        return
    await record_alert_event(
        db,
        scope=scope,
        metric=metric,
        value=value,
        threshold=threshold,
        message=message,
        node_id=node_id,
    )
    await _notify_owner(f"⚠️ <b>Observability alert</b>\n{message}")


async def observability_alerts_job():
    if not observability_settings.alerts_enabled:
        return
    try:
        async with GetDB() as db:
            from app.db.crud.admin import build_admin_details
            from app.db.crud.shop import get_owner_admin

            owner_db = await get_owner_admin(db)
            if owner_db is None:
                return
            owner = build_admin_details(owner_db)
            summary = await observability_operator.get_summary(db, owner)

            if summary.master is not None:
                resources = summary.master.resources
                mem_pct = (resources.mem_used / resources.mem_total * 100) if resources.mem_total else 0
                if resources.cpu_usage >= observability_settings.alert_cpu_threshold:
                    await _maybe_alert(
                        db,
                        scope="master",
                        metric="cpu",
                        value=resources.cpu_usage,
                        threshold=observability_settings.alert_cpu_threshold,
                        message=f"Panel CPU at {resources.cpu_usage:.1f}% (threshold {observability_settings.alert_cpu_threshold:.0f}%)",
                    )
                if mem_pct >= observability_settings.alert_mem_threshold:
                    await _maybe_alert(
                        db,
                        scope="master",
                        metric="memory",
                        value=mem_pct,
                        threshold=observability_settings.alert_mem_threshold,
                        message=f"Panel memory at {mem_pct:.1f}% (threshold {observability_settings.alert_mem_threshold:.0f}%)",
                    )

            for card in summary.nodes:
                if card.cpu_usage is not None and card.cpu_usage >= observability_settings.alert_cpu_threshold:
                    await _maybe_alert(
                        db,
                        scope="node",
                        metric="cpu",
                        value=card.cpu_usage,
                        threshold=observability_settings.alert_cpu_threshold,
                        message=f"Node <b>{card.name}</b> CPU at {card.cpu_usage:.1f}%",
                        node_id=card.node_id,
                    )
                if (
                    card.mem_usage_percent is not None
                    and card.mem_usage_percent >= observability_settings.alert_mem_threshold
                ):
                    await _maybe_alert(
                        db,
                        scope="node",
                        metric="memory",
                        value=card.mem_usage_percent,
                        threshold=observability_settings.alert_mem_threshold,
                        message=f"Node <b>{card.name}</b> memory at {card.mem_usage_percent:.1f}%",
                        node_id=card.node_id,
                    )
                if (
                    card.packet_loss_percent is not None
                    and card.packet_loss_percent >= observability_settings.alert_packet_loss_threshold
                ):
                    await _maybe_alert(
                        db,
                        scope="node",
                        metric="packet_loss",
                        value=card.packet_loss_percent,
                        threshold=observability_settings.alert_packet_loss_threshold,
                        message=f"Node <b>{card.name}</b> packet loss at {card.packet_loss_percent:.1f}%",
                        node_id=card.node_id,
                    )
    except Exception:
        logger.exception("observability_alerts_job failed")


if runtime_settings.role.runs_scheduler and observability_settings.alerts_enabled:
    scheduler.add_job(
        observability_alerts_job,
        "interval",
        seconds=observability_settings.alerts_interval,
        coalesce=True,
        max_instances=1,
        id="observability_alerts",
        replace_existing=True,
    )
