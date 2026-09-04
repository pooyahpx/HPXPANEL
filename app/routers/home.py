import asyncio

from fastapi import APIRouter, Depends, status
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import text

from app.db import AsyncSession, get_db
from app.nats import is_nats_enabled
from app.nats.node_rpc import node_nats_client
from app.nats.scheduler_rpc import scheduler_nats_client
from app.templates import render_template
from config import dashboard_settings, readiness_settings, runtime_settings, template_settings

DASHBOARD_ROUTE = dashboard_settings.path.rstrip("/")
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def base():
    return render_template(template_settings.home_page_template)


@router.get("/health", response_model=dict, status_code=status.HTTP_200_OK)
async def health():
    return {"status": "ok"}


def _failure(component: str, exc: Exception) -> dict[str, str]:
    return {"status": "down", "error": f"{component} check failed", "reason": exc.__class__.__name__}


async def _database_readiness(db: AsyncSession) -> dict[str, str]:
    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=readiness_settings.timeout)
        return {"status": "ok"}
    except Exception as exc:
        return _failure("database", exc)


async def _nats_readiness() -> dict[str, str]:
    try:
        client = await asyncio.wait_for(scheduler_nats_client.get_client(), timeout=readiness_settings.timeout)
        if client is None or not client.is_connected:
            raise RuntimeError("NATS is not connected")
        return {"status": "ok"}
    except Exception as exc:
        return _failure("NATS", exc)


async def _worker_readiness(client) -> dict[str, str]:
    try:
        result = await asyncio.wait_for(
            client.request("health_check", {}, readiness_settings.timeout),
            timeout=readiness_settings.timeout,
        )
        if result.get("status") != "ok":
            raise RuntimeError("worker returned an unhealthy response")
        return {"status": "ok"}
    except Exception as exc:
        return _failure("worker", exc)


@router.get("/ready", response_model=dict)
async def ready(db: AsyncSession = Depends(get_db)):
    checks: dict[str, dict[str, str]] = {"database": await _database_readiness(db)}

    if is_nats_enabled():
        checks["nats"] = await _nats_readiness()
        if runtime_settings.role.requires_nats:
            scheduler_check, node_check = await asyncio.gather(
                _worker_readiness(scheduler_nats_client),
                _worker_readiness(node_nats_client),
            )
            checks["scheduler_worker"] = scheduler_check
            checks["node_worker"] = node_check
    else:
        checks["nats"] = {"status": "disabled"}

    ready_status = all(check["status"] in {"ok", "disabled"} for check in checks.values())
    payload = {"status": "ready" if ready_status else "not_ready", "checks": checks}
    return JSONResponse(
        status_code=status.HTTP_200_OK if ready_status else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=payload,
    )
