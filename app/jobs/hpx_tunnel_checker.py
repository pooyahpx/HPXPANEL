from datetime import UTC, datetime as dt, timedelta as td

from app import scheduler
from app.db import GetDB
from app.db.crud.hpx_tunnel import get_hpx_tunnel_by_id, is_agent_managed, list_enabled_tunnels, update_hpx_tunnel
from app.db.models import HpxTunnelRole, HpxTunnelStatus
from app.operation import OperatorType
from app.operation.hpx_tunnel import HpxTunnelOperation
from app.services.hpx_tunnel.failover import (
    can_attempt_failback,
    can_attempt_failover,
)
from app.services.hpx_tunnel.healer import evaluate_and_repair
from app.services.hpx_tunnel.manager import health_ping_target, ping_host, start_tunnel, stop_container
from app.utils.logger import get_logger
from config import runtime_settings

logger = get_logger("hpx-tunnel-checker")
hpx_tunnel_operator = HpxTunnelOperation(operator_type=OperatorType.SYSTEM)


async def _notify_tunnel(title: str, detail: str | None = None) -> None:
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
            text = f"⚠️ HPX tunnel <b>{title}</b>"
            if detail:
                text += f"\n{detail}"
            await bot.send_message(owner.telegram_id, text, parse_mode="HTML")
    except Exception:
        logger.debug("Could not send HPX tunnel alert to owner", exc_info=True)


async def _activate_backup(db, backup, *, reason: str, primary_name: str) -> bool:
    now = dt.now(UTC)
    if is_agent_managed(backup):
        backup.agent_command = "restart"
        backup.status = HpxTunnelStatus.starting
        backup.message = f"Activated as failover for {primary_name}"
        backup.failover_of_tunnel_id = None
        backup.last_status_change = now
        await update_hpx_tunnel(
            db,
            backup,
            {
                "agent_command": backup.agent_command,
                "status": backup.status,
                "message": backup.message,
                "last_status_change": now,
                "enabled": True,
            },
        )
        return True

    if backup.role == HpxTunnelRole.iran:
        # Panel cannot start Iran Docker; queue agent if claimed, else skip.
        if backup.agent_key_hash:
            backup.agent_command = "start"
            backup.status = HpxTunnelStatus.starting
            backup.message = f"Activated as failover for {primary_name}"
            backup.last_status_change = now
            await update_hpx_tunnel(
                db,
                backup,
                {
                    "agent_command": backup.agent_command,
                    "status": backup.status,
                    "message": backup.message,
                    "last_status_change": now,
                    "enabled": True,
                },
            )
            return True
        return False

    password = await hpx_tunnel_operator._decrypt_password(db, backup)
    ok, err = await start_tunnel(backup, password)
    backup.status = HpxTunnelStatus.running if ok else HpxTunnelStatus.error
    backup.message = f"Activated as failover for {primary_name}" if ok else (err or "failover start failed")
    backup.last_status_change = now
    await update_hpx_tunnel(
        db,
        backup,
        {
            "status": backup.status,
            "message": backup.message,
            "last_status_change": backup.last_status_change,
            "enabled": True,
        },
    )
    return ok


async def _attempt_failover(db, db_tunnel) -> bool:
    ok, _reason = can_attempt_failover(db_tunnel)
    if not ok:
        return False

    backup = await get_hpx_tunnel_by_id(db, db_tunnel.backup_tunnel_id)
    if backup is None or backup.id == db_tunnel.id:
        return False

    reason = db_tunnel.message or "primary unhealthy"
    logger.warning("Failover: stopping tunnel %s, starting backup %s", db_tunnel.name, backup.name)

    now = dt.now(UTC)
    if is_agent_managed(db_tunnel):
        db_tunnel.agent_command = "stop"
    elif db_tunnel.role == HpxTunnelRole.foreign and db_tunnel.container_name:
        await stop_container(db_tunnel.container_name)

    ok = await _activate_backup(db, backup, reason=reason, primary_name=db_tunnel.name)
    if not ok:
        await _notify_tunnel(
            db_tunnel.name,
            f"Failover attempted to <b>{backup.name}</b> but backup failed to start.\nReason: {reason}",
        )
        return False

    backup.failover_of_tunnel_id = db_tunnel.id
    await update_hpx_tunnel(
        db,
        backup,
        {"failover_of_tunnel_id": db_tunnel.id, "failover_active": False},
    )

    db_tunnel.failover_active = True
    db_tunnel.status = HpxTunnelStatus.stopped
    db_tunnel.message = f"Failed over to backup tunnel #{backup.id}: {reason}"
    db_tunnel.last_failover_at = now
    db_tunnel.last_status_change = now
    await update_hpx_tunnel(
        db,
        db_tunnel,
        {
            "agent_command": db_tunnel.agent_command,
            "failover_active": True,
            "status": db_tunnel.status,
            "message": db_tunnel.message,
            "last_failover_at": now,
            "last_status_change": now,
        },
    )

    await _notify_tunnel(
        db_tunnel.name,
        f"Switched to backup <b>{backup.name}</b>\nReason: {reason}",
    )
    return True


async def _attempt_failback(db, db_tunnel) -> bool:
    """db_tunnel is the primary that previously failed over."""
    ok, _reason = can_attempt_failback(db_tunnel)
    if not ok:
        return False

    # Primary must look healthy again (runtime refresh already ran for Docker paths).
    if db_tunnel.status not in {HpxTunnelStatus.running}:
        # Try starting primary first if it is stopped after failover.
        if db_tunnel.status == HpxTunnelStatus.stopped and "Failed over" in (db_tunnel.message or ""):
            if is_agent_managed(db_tunnel):
                db_tunnel.agent_command = "restart"
                db_tunnel.status = HpxTunnelStatus.starting
                await update_hpx_tunnel(
                    db,
                    db_tunnel,
                    {
                        "agent_command": "restart",
                        "status": HpxTunnelStatus.starting,
                        "message": "Failback: restarting primary",
                        "last_status_change": dt.now(UTC),
                    },
                )
                return False  # wait for next cycle
            if db_tunnel.role == HpxTunnelRole.foreign:
                password = await hpx_tunnel_operator._decrypt_password(db, db_tunnel)
                ok, err = await start_tunnel(db_tunnel, password)
                if not ok:
                    return False
                db_tunnel.status = HpxTunnelStatus.running
                db_tunnel.message = err
                await update_hpx_tunnel(
                    db,
                    db_tunnel,
                    {"status": HpxTunnelStatus.running, "message": "Failback: primary restarted", "last_status_change": dt.now(UTC)},
                )
            else:
                return False
        else:
            return False

    backup = await get_hpx_tunnel_by_id(db, db_tunnel.backup_tunnel_id)
    now = dt.now(UTC)

    if backup is not None:
        if is_agent_managed(backup):
            backup.agent_command = "stop"
            await update_hpx_tunnel(
                db,
                backup,
                {
                    "agent_command": "stop",
                    "failover_of_tunnel_id": None,
                    "message": f"Standby after failback from {db_tunnel.name}",
                    "last_status_change": now,
                },
            )
        elif backup.role == HpxTunnelRole.foreign and backup.container_name:
            await stop_container(backup.container_name)
            await update_hpx_tunnel(
                db,
                backup,
                {
                    "status": HpxTunnelStatus.stopped,
                    "failover_of_tunnel_id": None,
                    "message": f"Standby after failback from {db_tunnel.name}",
                    "last_status_change": now,
                },
            )

    db_tunnel.failover_active = False
    db_tunnel.message = "Failback complete — primary path restored"
    db_tunnel.last_failover_at = now
    db_tunnel.last_status_change = now
    await update_hpx_tunnel(
        db,
        db_tunnel,
        {
            "failover_active": False,
            "status": HpxTunnelStatus.running,
            "message": db_tunnel.message,
            "last_failover_at": now,
            "last_status_change": now,
        },
    )
    await _notify_tunnel(db_tunnel.name, "Failback complete — primary path is healthy again")
    logger.info("Tunnel failback: %s restored", db_tunnel.name)
    return True


async def hpx_tunnel_checker_job():
    try:
        async with GetDB() as db:
            tunnels = await list_enabled_tunnels(db)
            # Also revisit stopped primaries that are in failover_active so failback can run.
            for db_tunnel in tunnels:
                if db_tunnel.status in {
                    HpxTunnelStatus.stopping,
                    HpxTunnelStatus.pending_claim,
                }:
                    continue

                if db_tunnel.failover_active and db_tunnel.status == HpxTunnelStatus.stopped:
                    await _attempt_failback(db, db_tunnel)
                    continue

                if db_tunnel.status == HpxTunnelStatus.stopped:
                    continue

                previous_status = db_tunnel.status
                db_tunnel = await hpx_tunnel_operator._refresh_runtime(db, db_tunnel)

                if previous_status == HpxTunnelStatus.running and db_tunnel.status in {
                    HpxTunnelStatus.error,
                    HpxTunnelStatus.unhealthy,
                }:
                    if db_tunnel.alert_on_down:
                        await _notify_tunnel(db_tunnel.name, db_tunnel.message)
                    await _attempt_failover(db, db_tunnel)

                if db_tunnel.failover_active and db_tunnel.status == HpxTunnelStatus.running:
                    await _attempt_failback(db, db_tunnel)

                # Agent-managed IRAN: metrics come from heartbeat only.
                if not is_agent_managed(db_tunnel):
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


if runtime_settings.role.runs_scheduler:
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
