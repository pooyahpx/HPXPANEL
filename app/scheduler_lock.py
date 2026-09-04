from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import logging
import os
import socket
import time
import uuid
from dataclasses import dataclass

from nats.js.errors import KeyDeletedError, KeyNotFoundError, KeyWrongLastSequenceError

from app.nats import is_nats_enabled
from app.nats.client import create_nats_client, get_jetstream_context
from config import nats_settings, scheduler_lock_settings

logger = logging.getLogger(__name__)


@dataclass
class SchedulerLease:
    key: str
    owner: str
    revision: int
    expires_at: float


class SchedulerLockManager:
    def __init__(self, *, clock=time.time, owner_id: str | None = None):
        self._clock = clock
        self._owner_id = owner_id or f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex}"
        self._nc = None
        self._kv = None
        self._connect_lock = asyncio.Lock()

    async def start(self) -> None:
        if not is_nats_enabled():
            return
        try:
            await self._get_kv()
        except Exception as exc:
            logger.warning("Scheduler lock backend is unavailable; jobs will fail closed: %s", exc)

    async def close(self) -> None:
        if self._nc is not None and not self._nc.is_closed:
            await self._nc.close()
        self._nc = None
        self._kv = None

    def set_kv_for_testing(self, kv) -> None:
        self._kv = kv

    async def _get_kv(self):
        if self._kv is not None and (self._nc is None or not self._nc.is_closed):
            return self._kv
        async with self._connect_lock:
            if self._kv is not None and (self._nc is None or not self._nc.is_closed):
                return self._kv
            await self.close()
            self._nc = await create_nats_client()
            if self._nc is None:
                raise RuntimeError("NATS is not available")
            js = await get_jetstream_context(self._nc)
            try:
                self._kv = await js.create_key_value(
                    bucket=nats_settings.scheduler_lock_kv_bucket,
                    history=1,
                    max_bytes=1024 * 1024,
                )
            except Exception:
                self._kv = await js.key_value(bucket=nats_settings.scheduler_lock_kv_bucket)
            return self._kv

    @staticmethod
    def _key(job_id: str) -> str:
        safe = "".join(char if char.isalnum() or char in "-_." else "_" for char in job_id)
        return f"job.{safe[:200]}"

    def _payload(self, expires_at: float) -> bytes:
        return json.dumps({"owner": self._owner_id, "expires_at": expires_at}, separators=(",", ":")).encode()

    async def acquire(self, job_id: str) -> SchedulerLease | None:
        if not is_nats_enabled():
            return SchedulerLease(self._key(job_id), self._owner_id, 0, float("inf"))

        kv = await self._get_kv()
        key = self._key(job_id)
        for _ in range(8):
            now = self._clock()
            expires_at = now + scheduler_lock_settings.lease_seconds
            try:
                entry = await kv.get(key)
            except KeyNotFoundError, KeyDeletedError:
                try:
                    revision = await kv.create(key, self._payload(expires_at))
                    return SchedulerLease(key, self._owner_id, revision, expires_at)
                except KeyWrongLastSequenceError:
                    continue

            try:
                state = json.loads(entry.value.decode())
                current_expiry = float(state["expires_at"])
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise RuntimeError(f"invalid scheduler lease state for {job_id}") from exc
            if current_expiry > now:
                return None
            try:
                revision = await kv.update(key, self._payload(expires_at), last=entry.revision)
                return SchedulerLease(key, self._owner_id, revision, expires_at)
            except KeyWrongLastSequenceError:
                continue
        return None

    async def renew(self, lease: SchedulerLease) -> bool:
        if not is_nats_enabled():
            return True
        try:
            kv = await self._get_kv()
            entry = await kv.get(lease.key)
            state = json.loads(entry.value.decode())
            now = self._clock()
            if state.get("owner") != lease.owner or float(state["expires_at"]) <= now:
                return False
            expires_at = now + scheduler_lock_settings.lease_seconds
            revision = await kv.update(lease.key, self._payload(expires_at), last=entry.revision)
            lease.revision = revision
            lease.expires_at = expires_at
            return True
        except Exception as exc:
            logger.warning("Scheduler lease renewal failed for %s: %s", lease.key, exc)
            return False

    async def release(self, lease: SchedulerLease) -> None:
        if not is_nats_enabled():
            return
        try:
            kv = await self._get_kv()
            entry = await kv.get(lease.key)
            state = json.loads(entry.value.decode())
            if state.get("owner") == lease.owner:
                await kv.delete(lease.key, last=entry.revision)
        except KeyNotFoundError, KeyDeletedError, KeyWrongLastSequenceError:
            return
        except Exception as exc:
            logger.warning("Scheduler lease release failed for %s: %s", lease.key, exc)

    async def _renew_until_done(
        self,
        lease: SchedulerLease,
        done: asyncio.Event,
        lost: asyncio.Event,
    ) -> None:
        while not done.is_set():
            try:
                await asyncio.wait_for(done.wait(), timeout=scheduler_lock_settings.renew_interval)
            except TimeoutError:
                try:
                    renewed = await asyncio.wait_for(
                        self.renew(lease),
                        timeout=scheduler_lock_settings.operation_timeout,
                    )
                except TimeoutError:
                    renewed = False
                if not renewed:
                    lost.set()
                    return

    async def run_locked(self, job_id: str, func, *args, **kwargs):
        try:
            lease = await asyncio.wait_for(
                self.acquire(job_id),
                timeout=scheduler_lock_settings.operation_timeout,
            )
        except Exception as exc:
            logger.error("Skipping scheduled job %s because its distributed lock is unavailable: %s", job_id, exc)
            return None
        if lease is None:
            logger.debug("Skipping scheduled job %s because another scheduler owns its lease", job_id)
            return None

        if not is_nats_enabled():
            return await _invoke(func, *args, **kwargs)

        done = asyncio.Event()
        lost = asyncio.Event()
        job_task = asyncio.create_task(_invoke(func, *args, **kwargs))
        renew_task = asyncio.create_task(self._renew_until_done(lease, done, lost))
        lost_task = asyncio.create_task(lost.wait())
        try:
            finished, _ = await asyncio.wait((job_task, lost_task), return_when=asyncio.FIRST_COMPLETED)
            if lost_task in finished and lost.is_set() and not job_task.done():
                logger.error("Cancelling scheduled job %s after losing its distributed lease", job_id)
                job_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await job_task
                return None
            return await job_task
        finally:
            done.set()
            renew_task.cancel()
            lost_task.cancel()
            await asyncio.gather(renew_task, lost_task, return_exceptions=True)
            try:
                await asyncio.wait_for(
                    self.release(lease),
                    timeout=scheduler_lock_settings.operation_timeout,
                )
            except TimeoutError:
                logger.warning("Scheduler lease release timed out for %s", lease.key)


async def _invoke(func, *args, **kwargs):
    if inspect.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    result = await asyncio.to_thread(func, *args, **kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


scheduler_lock_manager = SchedulerLockManager()
