from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.db import AsyncSession, get_db
from app.db.models import ShopOrderStatus
from app.models.admin import AdminDetails
from app.models.shop import (
    ShopApproveResponse,
    ShopConfigResponse,
    ShopConfigUpdate,
    ShopOrderListResponse,
    ShopOrderRejectRequest,
    ShopOrderResponse,
    ShopPlanCreate,
    ShopPlanResponse,
    ShopPlanUpdate,
    ShopStatsResponse,
)
from app.operation import OperatorType
from app.operation.shop import ShopOperation
from app.utils import responses

from .authentication import require_permission

router = APIRouter(tags=["Shop"], prefix="/api/shop", responses={401: responses._401, 403: responses._403})
shop_operator = ShopOperation(operator_type=OperatorType.API)


@router.get("/config", response_model=ShopConfigResponse)
async def get_shop_config(
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("users", "read")),
):
    """Get the current admin's Telegram/web shop configuration."""
    return await shop_operator.get_config(db, admin)


@router.put("/config", response_model=ShopConfigResponse)
async def update_shop_config(
    payload: ShopConfigUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("users", "create")),
):
    """Update shop enablement, cards, welcome note, and test-config settings."""
    return await shop_operator.update_config(db, admin, payload)


@router.get("/stats", response_model=ShopStatsResponse)
async def get_shop_stats(
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("users", "read")),
):
    """Aggregate buyer/order stats for the shop overview."""
    return await shop_operator.get_stats(db, admin)


@router.get("/plans", response_model=list[ShopPlanResponse])
async def list_shop_plans(
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("users", "read")),
):
    return await shop_operator.list_plans(db, admin)


@router.post("/plans", response_model=ShopPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_shop_plan(
    payload: ShopPlanCreate,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("users", "create")),
):
    return await shop_operator.create_plan(db, admin, payload)


@router.patch("/plans/{plan_id}", response_model=ShopPlanResponse)
async def update_shop_plan(
    plan_id: int,
    payload: ShopPlanUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("users", "create")),
):
    return await shop_operator.update_plan(db, admin, plan_id, payload)


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shop_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("users", "create")),
):
    await shop_operator.delete_plan(db, admin, plan_id)


@router.get("/orders", response_model=ShopOrderListResponse)
async def list_shop_orders(
    status_filter: Annotated[ShopOrderStatus | None, Query(alias="status")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("users", "read")),
):
    return await shop_operator.list_orders(db, admin, status=status_filter, offset=offset, limit=limit)


@router.get("/orders/{order_id}/receipt", responses={404: responses._404})
async def get_shop_order_receipt(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("users", "read")),
):
    """Proxy the Telegram receipt photo so the dashboard can display it."""
    content, media_type = await shop_operator.get_order_receipt(db, admin, order_id)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.post("/orders/{order_id}/approve", response_model=ShopApproveResponse)
async def approve_shop_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("users", "create")),
):
    """Approve a pending card-to-card order and create the panel user."""
    return await shop_operator.approve_order(db, admin, order_id)


@router.post("/orders/{order_id}/reject", response_model=ShopOrderResponse)
async def reject_shop_order(
    order_id: int,
    payload: ShopOrderRejectRequest | None = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("users", "create")),
):
    note = payload.note if payload else None
    return await shop_operator.reject_order(db, admin, order_id, note=note)
