import asyncio
import time

from aiogram.types import Update
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.db import AsyncSession, get_db
from app.db.crud.wireguard import get_subnet_usage
from app.models.admin import AdminDetails
from app.models.settings import Telegram
from app.models.system import (
    InboundSummary,
    IpGeoLookup,
    SystemResourceStats,
    SystemStats,
    SystemUsersStats,
    WireGuardSubnetUsage,
    WorkerHealth,
    WorkersHealth,
)
from app.utils.check_host_geo import lookup_check_host_ip
from app.nats import is_nats_enabled
from app.nats.node_rpc import node_nats_client
from app.nats.scheduler_rpc import scheduler_nats_client
from app.operation import OperatorType
from app.operation.system import SystemOperation
from app.settings import telegram_settings
from app.telegram import get_bot, get_dispatcher
from app.utils import responses
from app.utils.logger import EndpointFilter, get_logger
from config import telegram_env_settings

from .authentication import require_permission

system_operator = SystemOperation(operator_type=OperatorType.API)
router = APIRouter(tags=["System"], prefix="/api", responses={401: responses._401})

TELEGRAM_WEBHOOK_PATH = "/tghook"
if telegram_env_settings.do_not_log_bot:
    uvicorn_access_logger = get_logger("uvicorn.access")
    uvicorn_access_logger.addFilter(EndpointFilter([f"{router.prefix}{TELEGRAM_WEBHOOK_PATH}"]))


@router.get("/system", response_model=SystemStats)
async def get_system_stats(
    admin_username: str | None = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("system", "read")),
):
    """Fetch system stats including memory, CPU, disk, and user metrics."""
    return await system_operator.get_system_stats(db, admin=admin, admin_username=admin_username)


@router.get("/system/resources", response_model=SystemResourceStats)
async def get_system_resource_stats(
    _: AdminDetails = Depends(require_permission("system", "read")),
):
    """Fetch system resource stats without user metrics."""
    return await system_operator.get_system_resource_stats()


@router.get("/system/ip-geo", response_model=IpGeoLookup)
async def get_system_ip_geo(
    host: str,
    _: AdminDetails = Depends(require_permission("nodes", "read")),
):
    """Resolve country / ISP for a node IP using check-host.net."""
    info = await lookup_check_host_ip(host)
    if info is None:
        raise HTTPException(status_code=404, detail="IP geolocation not found")
    return IpGeoLookup(
        ip=info.ip,
        country=info.country,
        country_code=info.country_code,
        city=info.city,
        isp=info.isp,
        asn=info.asn,
        source=info.source,
    )


@router.get("/system/users", response_model=SystemUsersStats)
async def get_system_users_stats(
    admin_username: str | None = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("users", "read")),
):
    """Fetch user stats and traffic metrics without system resource stats."""
    return await system_operator.get_system_users_stats(db, admin=admin, admin_username=admin_username)


@router.get("/inbounds", response_model=list[str])
async def get_inbounds(_: AdminDetails = Depends(require_permission("system", "read"))):
    """Retrieve inbound configurations grouped by protocol."""
    return await system_operator.get_inbounds()


@router.get("/inbounds/details", response_model=list[InboundSummary])
async def get_inbound_details(_: AdminDetails = Depends(require_permission("system", "read"))):
    """Retrieve lightweight inbound metadata for dashboard forms."""
    return await system_operator.get_inbound_details()


@router.get("/wireguard/subnets", response_model=list[WireGuardSubnetUsage])
async def get_wireguard_subnets(
    db: AsyncSession = Depends(get_db),
    _: AdminDetails = Depends(require_permission("cores", "read")),
):
    """Per-subnet WireGuard address usage: capacity, used/free counts and the first free IPs."""
    return await get_subnet_usage(db)


async def _measure_worker_health(request_coro) -> WorkerHealth:
    start = time.monotonic()
    try:
        await request_coro
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return WorkerHealth(status="ok", response_time_ms=elapsed_ms)
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        error_msg = str(exc) or exc.__class__.__name__
        return WorkerHealth(status="down", response_time_ms=elapsed_ms, error=error_msg)


@router.get("/workers/health", response_model=WorkersHealth)
async def get_workers_health(_: AdminDetails = Depends(require_permission("system", "read"))):
    if not is_nats_enabled():
        disabled = WorkerHealth(status="disabled")
        return WorkersHealth(scheduler=disabled, node=disabled)

    timeout = 5.0
    scheduler_task = _measure_worker_health(scheduler_nats_client.request("health_check", {}, timeout))
    node_task = _measure_worker_health(node_nats_client.request("health_check", {}, timeout))
    scheduler_health, node_health = await asyncio.gather(scheduler_task, node_task)

    return WorkersHealth(scheduler=scheduler_health, node=node_health)


@router.post(TELEGRAM_WEBHOOK_PATH, include_in_schema=False)
async def webhook_handler(request: Request, X_Telegram_Bot_Api_Secret_Token: str = Header()):
    """Telegram webhook handler"""
    settings: Telegram = await telegram_settings()

    if not settings.enable:
        raise HTTPException(status_code=404, detail="not found")

    if X_Telegram_Bot_Api_Secret_Token != settings.webhook_secret:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid secret key")

    bot = get_bot()
    if not bot:
        return JSONResponse(status_code=200, content={"status": "ok"})
    dp = get_dispatcher()

    update_data = await request.json()
    update = Update.model_validate(update_data, context={"bot": bot})
    asyncio.create_task(dp.feed_update(bot, update))
    return JSONResponse(status_code=200, content={"status": "ok"})
