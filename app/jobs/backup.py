from datetime import UTC, datetime, timedelta

from app import scheduler
from app.backup.service import get_state
from app.db import GetDB
from app.operation import OperatorType
from app.operation.backup import BackupOperation, notify_backup_failure
from app.utils.logger import get_logger
from config import backup_settings, runtime_settings

logger = get_logger("backup-job")
backup_operator = BackupOperation(operator_type=OperatorType.SYSTEM)


async def scheduled_backup_job():
    try:
        async with GetDB() as db:
            config = await backup_operator.get_config(db)
            if not config.auto_enabled:
                return
            state = get_state()
            last_success = state.get("last_success_at")
            if isinstance(last_success, datetime) and datetime.now(UTC) - last_success < timedelta(
                hours=config.schedule_hours
            ):
                return
            await backup_operator.run_backup(db)
            logger.info("Scheduled HPXPANEL backup completed")
    except Exception as exc:
        logger.exception("scheduled_backup_job failed")
        await notify_backup_failure(f"Scheduled panel backup failed: {exc}")


if runtime_settings.role.runs_scheduler:
    scheduler.add_job(
        scheduled_backup_job,
        "interval",
        seconds=backup_settings.job_interval,
        coalesce=True,
        max_instances=1,
        id="panel_backup",
        replace_existing=True,
    )
