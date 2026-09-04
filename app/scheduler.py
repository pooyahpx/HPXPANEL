from functools import wraps

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.scheduler_lock import scheduler_lock_manager


class LeaseProtectedScheduler(AsyncIOScheduler):
    def add_job(self, func, *args, **kwargs):
        job_id = kwargs.get("id") or f"{func.__module__}.{func.__qualname__}"

        @wraps(func)
        async def locked_job(*job_args, **job_kwargs):
            return await scheduler_lock_manager.run_locked(job_id, func, *job_args, **job_kwargs)

        return super().add_job(locked_job, *args, **kwargs)


scheduler = LeaseProtectedScheduler(job_defaults={"max_instances": 30}, timezone="UTC")
