from app import scheduler
from app.db import GetDB
from app.db.crud.observability import purge_old_node_stats, purge_old_system_stats
from app.utils.logger import get_logger
from config import database_settings, observability_settings, runtime_settings

logger = get_logger("observability-retention")


async def observability_retention_job():
    if not database_settings.is_postgresql:
        return
    retention_days = observability_settings.retention_days
    async with GetDB() as db:
        node_deleted = await purge_old_node_stats(db, retention_days=retention_days)
        system_deleted = await purge_old_system_stats(db, retention_days=retention_days)
    if node_deleted or system_deleted:
        logger.info(
            "Observability retention: removed %s node_stats and %s system_stats rows older than %s days",
            node_deleted,
            system_deleted,
            retention_days,
        )


if database_settings.is_postgresql and runtime_settings.role.runs_scheduler:
    scheduler.add_job(
        observability_retention_job,
        "interval",
        seconds=observability_settings.retention_interval,
        coalesce=True,
        max_instances=1,
        id="observability_retention",
        replace_existing=True,
    )
