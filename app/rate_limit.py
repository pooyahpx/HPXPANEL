from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import logging
import math
import time
from dataclasses import dataclass
from typing import Protocol

from fastapi import HTTPException, Request, status
from nats.js.errors import KeyDeletedError, KeyNotFoundError, KeyWrongLastSequenceError

from app.nats import is_nats_enabled
from app.nats.client import create_nats_client, get_jetstream_context
from config import nats_settings, rate_limit_settings, runtime_settings, server_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitPolicy:
    name: str
    limit: int
    window: int


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after: int = 0


class RateLimitBackend(Protocol):
    async def check(self, key: str, policy: RateLimitPolicy) -> RateLimitResult: ...

    async def close(self) -> None: ...


def normalize_client_ip(request: Request) -> str:
    value = request.client.host.strip() if request.client and request.client.host else "unknown"
    try:
        address = ipaddress.ip_address(value)
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            address = address.ipv4_mapped
        return address.compressed
    except ValueError:
        return value.casefold()[:128] or "unknown"


def _key_for(request: Request, endpoint: str, identity: str | None) -> str:
    normalized_identity = (identity or "-").strip().casefold()
    material = "\0".join((normalize_client_ip(request), endpoint, normalized_identity))
    return hashlib.sha256(material.encode()).hexdigest()


class InMemoryRateLimitBackend:
    def __init__(self, max_keys: int, clock=time.monotonic):
        self._max_keys = max_keys
        self._clock = clock
        self._entries: dict[str, tuple[int, float]] = {}
        self._lock = asyncio.Lock()

    async def check(self, key: str, policy: RateLimitPolicy) -> RateLimitResult:
        now = self._clock()
        async with self._lock:
            current = self._entries.get(key)
            if current is None or current[1] <= now:
                self._entries[key] = (1, now + policy.window)
                self._cleanup(now)
                return RateLimitResult(True)

            count, reset_at = current
            if count >= policy.limit:
                return RateLimitResult(False, max(1, math.ceil(reset_at - now)))

            self._entries[key] = (count + 1, reset_at)
            return RateLimitResult(True)

    def _cleanup(self, now: float) -> None:
        if len(self._entries) <= self._max_keys:
            return
        expired = [key for key, (_, reset_at) in self._entries.items() if reset_at <= now]
        for key in expired:
            self._entries.pop(key, None)
        if len(self._entries) > self._max_keys:
            overflow = len(self._entries) - self._max_keys
            oldest = sorted(self._entries, key=lambda item: self._entries[item][1])[:overflow]
            for key in oldest:
                self._entries.pop(key, None)

    async def close(self) -> None:
        self._entries.clear()


class NatsRateLimitBackend:
    def __init__(self, clock=time.time):
        self._clock = clock
        self._nc = None
        self._kv = None
        self._connect_lock = asyncio.Lock()

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
                    bucket=nats_settings.rate_limit_kv_bucket,
                    history=1,
                    max_bytes=16 * 1024 * 1024,
                    ttl=max(
                        rate_limit_settings.admin_login_window,
                        rate_limit_settings.setup_window,
                        rate_limit_settings.pulse_claim_window,
                        rate_limit_settings.subscription_window,
                    )
                    * 2,
                )
            except Exception:
                self._kv = await js.key_value(bucket=nats_settings.rate_limit_kv_bucket)
            return self._kv

    async def check(self, key: str, policy: RateLimitPolicy) -> RateLimitResult:
        kv = await self._get_kv()
        storage_key = f"limit.{policy.name}.{key}"
        for _ in range(8):
            now = self._clock()
            try:
                entry = await kv.get(storage_key)
            except KeyNotFoundError, KeyDeletedError:
                payload = json.dumps({"count": 1, "reset_at": now + policy.window}).encode()
                try:
                    await kv.create(storage_key, payload)
                    return RateLimitResult(True)
                except KeyWrongLastSequenceError:
                    continue

            try:
                value = json.loads(entry.value.decode())
                count = int(value["count"])
                reset_at = float(value["reset_at"])
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise RuntimeError("invalid rate-limit state in NATS") from exc

            if reset_at <= now:
                count = 0
                reset_at = now + policy.window
            if count >= policy.limit:
                return RateLimitResult(False, max(1, math.ceil(reset_at - now)))

            payload = json.dumps({"count": count + 1, "reset_at": reset_at}).encode()
            try:
                await kv.update(storage_key, payload, last=entry.revision)
                return RateLimitResult(True)
            except KeyWrongLastSequenceError:
                continue
        raise RuntimeError("rate-limit contention exceeded retry budget")

    async def close(self) -> None:
        if self._nc is not None and not self._nc.is_closed:
            await self._nc.close()
        self._nc = None
        self._kv = None


class RateLimiter:
    def __init__(self):
        self._backend: RateLimitBackend | None = None

    async def start(self) -> None:
        distributed = is_nats_enabled() and (runtime_settings.role.requires_nats or server_settings.workers > 1)
        self._backend = (
            NatsRateLimitBackend() if distributed else InMemoryRateLimitBackend(rate_limit_settings.memory_max_keys)
        )

    async def close(self) -> None:
        if self._backend is not None:
            await self._backend.close()
        self._backend = None

    def set_backend_for_testing(self, backend: RateLimitBackend) -> None:
        self._backend = backend

    async def enforce(
        self,
        request: Request,
        endpoint: str,
        limit: int,
        window: int,
        *,
        identity: str | None = None,
    ) -> None:
        if not rate_limit_settings.enabled:
            return
        if self._backend is None:
            await self.start()
        policy = RateLimitPolicy(endpoint, limit, window)
        try:
            result = await asyncio.wait_for(
                self._backend.check(_key_for(request, endpoint, identity), policy),
                timeout=rate_limit_settings.backend_timeout,
            )
        except Exception as exc:
            logger.warning("Distributed rate limiter unavailable for %s: %s", endpoint, exc)
            if isinstance(self._backend, NatsRateLimitBackend):
                retry_after = rate_limit_settings.unavailable_retry_after
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Rate limiter temporarily unavailable",
                    headers={"Retry-After": str(retry_after)},
                ) from exc
            raise
        if not result.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests",
                headers={"Retry-After": str(result.retry_after)},
            )

    async def enforce_client_and_identity(
        self,
        request: Request,
        endpoint: str,
        limit: int,
        window: int,
        *,
        identity: str,
    ) -> None:
        """Apply full-size aggregate client and client+identity buckets."""
        await self.enforce(request, f"{endpoint}-client", limit, window)
        await self.enforce(request, f"{endpoint}-identity", limit, window, identity=identity)


rate_limiter = RateLimiter()
