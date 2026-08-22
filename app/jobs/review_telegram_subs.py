from datetime import UTC, datetime as dt, timedelta as td

from app import scheduler
from app.telegram.utils.sub_delivery import scan_all_telegram_subs
from app.utils.logger import get_logger
from config import job_settings

logger = get_logger("review-telegram-subs")


async def review_telegram_subs_job():
    try:
        notified = await scan_all_telegram_subs()
        if notified:
            logger.info("Sent %s telegram sub update(s)", notified)
    except Exception:
        logger.exception("review_telegram_subs_job failed")


if scheduler:
    interval = max(60, job_settings.review_users_interval)
    now = dt.now(UTC)
    scheduler.add_job(
        review_telegram_subs_job,
        "interval",
        seconds=interval,
        coalesce=True,
        max_instances=1,
        start_date=now + td(seconds=15),
        id="review_telegram_subs",
        replace_existing=True,
    )
