"""Telegram Mini App — public SPA + initData-authenticated shop/admin APIs."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from aiogram.utils.web_app import WebAppInitData, safe_parse_webapp_init_data
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.db.crud.admin import get_admin_by_telegram_id
from app.db.crud.shop import (
    get_or_create_telegram_profile,
    get_shop_config_by_admin,
    list_active_plans,
    list_buyer_orders,
    list_enabled_shop_configs,
    set_preferred_shop_admin,
    set_telegram_lang,
)
from app.db.crud.shop_wallet import ensure_referral_code, get_or_create_wallet
from app.db.models import AdminStatus
from app.models.settings import Telegram
from app.settings import telegram_settings
from app.telegram.utils.i18n import format_bytes
from app.telegram.utils.shop_helpers import get_buyer_shop_config, shop_cards
from app.utils import responses
from app.utils.helpers import resolve_panel_base_url

STATIC_DIR = Path(__file__).resolve().parents[1] / "telegram" / "miniapp" / "static"

router = APIRouter(
    tags=["Telegram Mini App"],
    prefix="/api/telegram/miniapp",
    responses={401: responses._401, 403: responses._403},
)

public_router = APIRouter(tags=["Telegram Mini App"])


class MiniAppLangBody(BaseModel):
    lang: Annotated[str, Field(pattern="^(fa|en)$")]


class MiniAppSession(BaseModel):
    ok: bool = True
    user: dict[str, Any]
    lang: str
    is_admin: bool = False
    admin_username: str | None = None
    bot_username: str | None = None
    panel_url: str | None = None
    shop: dict[str, Any] | None = None
    features: dict[str, bool] = Field(default_factory=dict)


async def _parse_init_data(raw: str) -> WebAppInitData:
    settings: Telegram = await telegram_settings()
    if not settings.enable or not settings.token:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Telegram bot is disabled")
    if not settings.mini_app_login:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Mini App login is disabled")
    try:
        return safe_parse_webapp_init_data(token=settings.token, init_data=raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid Telegram init data",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def require_miniapp_user(
    request: Request,
    x_telegram_init_data: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> WebAppInitData:
    raw = (x_telegram_init_data or "").strip()
    if not raw and authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() in ("tma", "bearer") and token.strip():
            raw = token.strip()
    if not raw:
        raw = (request.query_params.get("tgWebAppData") or "").strip()
    if not raw:
        raise HTTPException(status_code=401, detail="missing Telegram init data")
    return await _parse_init_data(raw)


async def _bot_username() -> str | None:
    try:
        from app.telegram import get_bot

        bot = get_bot()
        if bot is None:
            return None
        me = await bot.get_me()
        return me.username
    except Exception:
        return None


def _shop_payload(config) -> dict[str, Any]:
    return {
        "admin_id": config.admin_id,
        "enabled": bool(config.enabled),
        "welcome_note": config.welcome_note or "",
        "tutorial_text": config.tutorial_text or "",
        "tutorial_url": config.tutorial_url or "",
        "referral_reward_toman": int(getattr(config, "referral_reward_toman", 0) or 0),
        "referral_reward_data_gb": float(getattr(config, "referral_reward_data_gb", 0) or 0),
        "cards": shop_cards(config),
        "features": {
            "wallet": bool(getattr(config, "wallet_enabled", False)),
            "referral": bool(getattr(config, "referral_enabled", False)),
            "test": bool(getattr(config, "test_enabled", False)),
            "tutorial": bool(getattr(config, "tutorial_enabled", False)),
            "server_status": bool(
                getattr(config, "server_status_enabled", False) and getattr(config, "server_status_group_id", None)
            ),
            "custom": bool(getattr(config, "custom_enabled", False)),
        },
    }


@router.post("/session", response_model=MiniAppSession)
async def miniapp_session(
    init: WebAppInitData = Depends(require_miniapp_user),
    db: AsyncSession = Depends(get_db),
):
    tg_user = init.user
    telegram_id = int(tg_user.id)
    profile = await get_or_create_telegram_profile(db, telegram_id)
    lang = profile.lang or "fa"

    db_admin = await get_admin_by_telegram_id(db, telegram_id, load_users=False, load_usage_logs=False)
    is_admin = db_admin is not None and getattr(db_admin, "status", None) != AdminStatus.disabled

    config = await get_buyer_shop_config(db, None, telegram_id=telegram_id, require_selection=False)
    if config is None:
        shops = await list_enabled_shop_configs(db)
        config = shops[0][0] if shops else None
    if config is not None:
        await set_preferred_shop_admin(db, telegram_id, config.admin_id)

    settings = await telegram_settings()
    panel_url = (settings.panel_url or "").strip() or await resolve_panel_base_url()

    features = {
        "shop": config is not None and bool(config.enabled),
        "admin": is_admin,
        "open_panel": is_admin and bool(panel_url),
    }
    if config is not None:
        features.update(_shop_payload(config)["features"])

    return MiniAppSession(
        user={
            "id": telegram_id,
            "first_name": tg_user.first_name or "",
            "last_name": tg_user.last_name or "",
            "username": tg_user.username or "",
            "photo_url": getattr(tg_user, "photo_url", None) or "",
        },
        lang=lang,
        is_admin=is_admin,
        admin_username=db_admin.username if db_admin else None,
        bot_username=await _bot_username(),
        panel_url=panel_url or None,
        shop=_shop_payload(config) if config is not None else None,
        features=features,
    )


@router.post("/lang")
async def miniapp_set_lang(
    body: MiniAppLangBody,
    init: WebAppInitData = Depends(require_miniapp_user),
    db: AsyncSession = Depends(get_db),
):
    await set_telegram_lang(db, int(init.user.id), body.lang)
    return {"ok": True, "lang": body.lang}


@router.get("/plans")
async def miniapp_plans(
    init: WebAppInitData = Depends(require_miniapp_user),
    db: AsyncSession = Depends(get_db),
    shop_admin_id: int | None = Query(default=None),
):
    telegram_id = int(init.user.id)
    config = await get_buyer_shop_config(db, None, telegram_id=telegram_id, require_selection=False)
    if shop_admin_id:
        cfg = await get_shop_config_by_admin(db, shop_admin_id)
        if cfg and cfg.enabled:
            config = cfg
            await set_preferred_shop_admin(db, telegram_id, cfg.admin_id)
    if not config or not config.enabled:
        raise HTTPException(status_code=404, detail="shop unavailable")
    plans = await list_active_plans(db, config.admin_id)
    return {
        "shop_admin_id": config.admin_id,
        "plans": [
            {
                "id": p.id,
                "name": p.name,
                "price_toman": int(p.price_toman or 0),
                "data_limit": int(p.data_limit or 0),
                "data_label": format_bytes(int(p.data_limit or 0)),
                "expire_days": int(p.expire_days or 0),
            }
            for p in plans
        ],
    }


@router.get("/orders")
async def miniapp_orders(
    init: WebAppInitData = Depends(require_miniapp_user),
    db: AsyncSession = Depends(get_db),
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
):
    orders = await list_buyer_orders(db, int(init.user.id), limit=limit)
    return {
        "orders": [
            {
                "id": o.id,
                "status": getattr(o.status, "value", o.status),
                "order_kind": o.order_kind,
                "quoted_price_toman": o.quoted_price_toman,
                "requested_username": o.requested_username,
                "payment_method": o.payment_method,
                "payment_paid": bool(o.payment_paid),
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "plan_id": o.plan_id,
            }
            for o in orders
        ]
    }


@router.get("/wallet")
async def miniapp_wallet(
    init: WebAppInitData = Depends(require_miniapp_user),
    db: AsyncSession = Depends(get_db),
):
    telegram_id = int(init.user.id)
    config = await get_buyer_shop_config(db, None, telegram_id=telegram_id, require_selection=False)
    if not config or not config.enabled or not getattr(config, "wallet_enabled", False):
        raise HTTPException(status_code=404, detail="wallet unavailable")
    wallet = await get_or_create_wallet(db, config.admin_id, telegram_id)
    return {
        "balance_toman": int(wallet.balance_toman or 0),
        "shop_admin_id": config.admin_id,
    }


@router.get("/referral")
async def miniapp_referral(
    init: WebAppInitData = Depends(require_miniapp_user),
    db: AsyncSession = Depends(get_db),
):
    telegram_id = int(init.user.id)
    config = await get_buyer_shop_config(db, None, telegram_id=telegram_id, require_selection=False)
    if not config or not config.enabled or not getattr(config, "referral_enabled", False):
        raise HTTPException(status_code=404, detail="referral unavailable")
    code = await ensure_referral_code(db, telegram_id)
    bot_username = await _bot_username()
    link = f"https://t.me/{bot_username}?start=ref_{code}" if bot_username else None
    return {
        "code": code,
        "link": link,
        "reward_toman": int(getattr(config, "referral_reward_toman", 0) or 0),
        "reward_data_gb": float(getattr(config, "referral_reward_data_gb", 0) or 0),
    }


@router.get("/server-status")
async def miniapp_server_status(
    init: WebAppInitData = Depends(require_miniapp_user),
    db: AsyncSession = Depends(get_db),
):
    telegram_id = int(init.user.id)
    config = await get_buyer_shop_config(db, None, telegram_id=telegram_id, require_selection=False)
    if (
        not config
        or not config.enabled
        or not getattr(config, "server_status_enabled", False)
        or not getattr(config, "server_status_group_id", None)
    ):
        raise HTTPException(status_code=404, detail="server status unavailable")
    from app.telegram.utils.server_status import load_server_status

    view = await load_server_status(db, int(config.server_status_group_id))
    if view is None:
        raise HTTPException(status_code=404, detail="status group missing")
    return {
        "hosts": [{"name": name, "status": status_} for name, status_ in view.host_rows],
        "pulses": [{"name": name, "status": status_} for name, status_ in view.pulse_rows],
    }


@public_router.get("/miniapp", response_class=HTMLResponse)
@public_router.get("/miniapp/", response_class=HTMLResponse)
async def miniapp_index():
    index = STATIC_DIR / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=404, detail="Mini App not packaged")
    return FileResponse(index, media_type="text/html")


@public_router.get("/miniapp/{asset_path:path}")
async def miniapp_asset(asset_path: str):
    target = (STATIC_DIR / asset_path).resolve()
    root = STATIC_DIR.resolve()
    if not str(target).startswith(str(root)) or not target.is_file():
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(target)
