from datetime import UTC, datetime as dt, timedelta as td

from app import scheduler
from app.db import GetDB
from app.db.crud.hpx_tunnel import get_hpx_tunnel_by_id, is_agent_managed, list_enabled_tunnels, update_hpx_tunnel
from app.db.models import HpxTunnelRole, HpxTunnelStatus
from app.operation import OperatorType
from app.operation.hpx_tunnel import HpxTunnelOperation
from app.services.hpx_tunnel.healer import evaluate_and_repair
from app.services.hpx_tunnel.manager import health_ping_target, ping_host, start_tunnel, stop_container
from app.utils.logger import get_logger

logger = get_logger("hpx-tunnel-checker")
hpx_tunnel_operator = HpxTunnelOperation(operator_type=OperatorType.SYSTEM)


async def _notify_tunnel_down(tunnel_name: str, message: str | None) -> None:
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
            text = f"⚠️ HPX tunnel <b>{tunnel_name}</b> is down"
            if message:
                text += f"\n{message}"
            await bot.send_message(owner.telegram_id, text, parse_mode="HTML")
    except Exception:
        logger.debug("Could not send HPX tunnel alert to owner", exc_info=True)


async def _attempt_failover(db, db_tunnel) -> None:
    if not db_tunnel.auto_failover or not db_tunnel.backup_tunnel_id:
        return
    backup = await get_hpx_tunnel_by_id(db, db_tunnel.backup_tunnel_id)
    if backup is None or backup.id == db_tunnel.id:
        return
    if is_agent_managed(backup) or backup.role == HpxTunnelRole.iran:
        return

    logger.warning("Failover: stopping tunnel %s, starting backup %s", db_tunnel.name, backup.name)
    await stop_container(db_tunnel.container_name)
    password = await hpx_tunnel_operator._decrypt_password(db, backup)
    ok, err = await start_tunnel(backup, password)
    if ok:
        backup.status = HpxTunnelStatus.running
        backup.message = f"Activated as failover for {db_tunnel.name}"
    else:
        backup.status = HpxTunnelStatus.error
        backup.message = err
    backup.last_status_change = dt.now(UTC)
    await update_hpx_tunnel(
        db,
        backup,
        {
            "status": backup.status,
            "message": backup.message,
            "last_status_change": backup.last_status_change,
        },
    )


async def hpx_tunnel_checker_job():
    try:
        async with GetDB() as db:
            tunnels = await list_enabled_tunnels(db)
            for db_tunnel in tunnels:
                if db_tunnel.status in {
                    HpxTunnelStatus.stopped,
                    HpxTunnelStatus.stopping,
                    HpxTunnelStatus.pending_claim,
                }:
                    continue

                previous_status = db_tunnel.status
                db_tunnel = await hpx_tunnel_operator._refresh_runtime(db, db_tunnel)

                if previous_status == HpxTunnelStatus.running and db_tunnel.status in {
                    HpxTunnelStatus.error,
                    HpxTunnelStatus.unhealthy,
                }:
                    if db_tunnel.alert_on_down:
                        await _notify_tunnel_down(db_tunnel.name, db_tunnel.message)
                    if not is_agent_managed(db_tunnel):
                        await _attempt_failover(db, db_tunnel)

                target = health_ping_target(db_tunnel)
                if target:
                    latency, loss = await ping_host(target)
                    await update_hpx_tunnel(
                        db,
                        db_tunnel,
                        {"latency_ms": latency, "packet_loss_pct": loss, "last_health_check": dt.now(UTC)},
                    )

                if db_tunnel.auto_heal_enabled and db_tunnel.status not in {
                    HpxTunnelStatus.stopped,
                    HpxTunnelStatus.stopping,
                    HpxTunnelStatus.pending_claim,
                }:
                    password = None
                    if db_tunnel.role == HpxTunnelRole.foreign and not is_agent_managed(db_tunnel):
                        password = await hpx_tunnel_operator._decrypt_password(db, db_tunnel)
                    heal = await evaluate_and_repair(db_tunnel, password=password, auto=True)
                    if heal.repaired and db_tunnel.role == HpxTunnelRole.foreign and not is_agent_managed(db_tunnel):
                        db_tunnel = await hpx_tunnel_operator._refresh_runtime(db, db_tunnel)

            await db.commit()
    except Exception:
        logger.exception("hpx_tunnel_checker_job failed")


if scheduler:
    now = dt.now(UTC)
    scheduler.add_job(
        hpx_tunnel_checker_job,
        "interval",
        seconds=60,
        coalesce=True,
        max_instances=1,
        start_date=now + td(seconds=30),
        id="hpx_tunnel_checker",
        replace_existing=True,
    )
