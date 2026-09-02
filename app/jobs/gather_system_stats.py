from app import scheduler
from app.db import GetDB
from app.db.crud.observability import insert_system_stat
from app.db.models import SystemStat
from app.operation.system import SystemOperation
from app.utils.logger import get_logger
from config import database_settings, observability_settings, runtime_settings

logger = get_logger("gather-system-stats")


async def gather_system_stats():
    try:
        resources = await SystemOperation.get_system_resource_stats()
    except Exception:
        logger.exception("Failed to gather system stats")
        return

    stat = SystemStat(
        mem_total=resources.mem_total,
        mem_used=resources.mem_used,
        cpu_cores=resources.cpu_cores,
        cpu_usage=resources.cpu_usage,
        incoming_bandwidth_speed=0,
        outgoing_bandwidth_speed=0,
        disk_total=resources.disk_total,
        disk_used=resources.disk_used,
    )
    async with GetDB() as db:
        await insert_system_stat(db, stat)


if database_settings.is_postgresql and runtime_settings.role.runs_panel:
    scheduler.add_job(
        gather_system_stats,
        "interval",
        seconds=observability_settings.system_stats_interval,
        coalesce=True,
        max_instances=1,
        id="gather_system_stats",
        replace_existing=True,
    )
