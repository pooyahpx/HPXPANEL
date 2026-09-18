from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import HTMLResponse

from app.db import AsyncSession, get_db
from app.db.crud.shop import get_shop_config_by_admin, get_shop_order, update_shop_order_payment
from app.db.models import ShopOrderStatus
from app.models.admin import AdminDetails
from app.models.shop import (
    CreateBudgetLedgerEntry,
    CreateBudgetLedgerListResponse,
    CreateBudgetSettleRequest,
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
from app.shop.payments import (
    GATEWAY_IDPAY,
    GATEWAY_NOWPAYMENTS,
    GATEWAY_PAYPAL,
    GATEWAY_STRIPE,
    GATEWAY_ZARINPAL,
    capture_paypal,
    verify_idpay,
    verify_nowpayments_signature,
    verify_stripe_signature,
    verify_zarinpal,
)
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
    order_kind: Annotated[str | None, Query()] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("users", "read")),
):
    kind = (order_kind or "").strip().lower() or None
    if kind and kind not in ("purchase", "renewal"):
        kind = None
    return await shop_operator.list_orders(
        db, admin, status=status_filter, order_kind=kind, offset=offset, limit=limit
    )


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


@router.get("/accounting", response_model=CreateBudgetLedgerListResponse)
async def list_create_budget_accounting(
    admin_id: Annotated[int | None, Query()] = None,
    settled: Annotated[bool | None, Query()] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("users", "read")),
):
    """Create-budget accounting ledger (owner: all/filter; admin: own only)."""
    return await shop_operator.list_create_budget_accounting(
        db, admin, admin_id=admin_id, settled=settled, offset=offset, limit=limit
    )


@router.post("/accounting/{entry_id}/settle", response_model=CreateBudgetLedgerEntry)
async def settle_create_budget_entry(
    entry_id: int,
    payload: CreateBudgetSettleRequest | None = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("users", "update")),
):
    """Mark a create-budget ledger row as settled (or unsettled) with the owner."""
    settled = True if payload is None else bool(payload.settled)
    return await shop_operator.settle_create_budget_entry(db, admin, entry_id, settled=settled)


def _payment_done_html(ok: bool, order_id: int | None = None) -> HTMLResponse:
    if ok:
        body = (
            f"<h2>Payment received</h2>"
            f"<p>Order #{order_id or '?'} is being activated. You can return to Telegram.</p>"
        )
    else:
        body = (
            "<h2>Payment not confirmed</h2>"
            "<p>If you were charged, contact support with your order id.</p>"
        )
    return HTMLResponse(
        "<!doctype html><html><head><meta charset='utf-8'><title>Shop payment</title></head>"
        f"<body style='font-family:sans-serif;max-width:480px;margin:3rem auto;padding:1rem'>{body}</body></html>"
    )


def _safe_int(value) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


@router.api_route("/payments/return", methods=["GET", "POST"], include_in_schema=False)
async def payment_return(
    request: Request,
    order_id: Annotated[int | None, Query()] = None,
    Authority: Annotated[str | None, Query()] = None,
    Status: Annotated[str | None, Query()] = None,
    id: Annotated[str | None, Query()] = None,
    token: Annotated[str | None, Query()] = None,
    session_id: Annotated[str | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
):
    """Browser return URL after Zarinpal / IDPay / PayPal / Stripe / NOWPayments."""
    form: dict = {}
    if request.method == "POST":
        try:
            form = dict(await request.form())
        except Exception:
            form = {}
    oid = order_id or _safe_int(form.get("order_id"))
    if oid is None:
        return _payment_done_html(False)
    order = await get_shop_order(db, oid)
    if order is None:
        return _payment_done_html(False, oid)
    config = await get_shop_config_by_admin(db, order.admin_id)
    if config is None:
        return _payment_done_html(False, oid)

    method = (order.payment_method or "").lower()
    amount = int(order.quoted_price_toman or 0)
    paid = False
    try:
        if method == GATEWAY_ZARINPAL:
            authority = Authority or form.get("Authority") or order.payment_ref
            st = (Status or form.get("Status") or "").upper()
            if st == "OK" and authority:
                paid = await verify_zarinpal(config, authority=str(authority), amount_toman=amount)
        elif method == GATEWAY_IDPAY:
            pay_id = id or form.get("id") or order.payment_ref
            if pay_id:
                paid = await verify_idpay(config, payment_id=str(pay_id), order_id=oid)
        elif method == GATEWAY_PAYPAL:
            paypal_id = token or form.get("token") or order.payment_ref
            if paypal_id:
                paid = await capture_paypal(config, paypal_order_id=str(paypal_id))
        elif method == GATEWAY_STRIPE or method == GATEWAY_NOWPAYMENTS:
            paid = bool(order.payment_paid)
    except Exception:
        paid = False

    if paid and order.status == ShopOrderStatus.pending:
        await shop_operator.fulfill_paid_order(db, oid)
        return _payment_done_html(True, oid)
    if order.status == ShopOrderStatus.approved or order.payment_paid:
        return _payment_done_html(True, oid)
    return _payment_done_html(False, oid)


@router.post("/payments/nowpayments/callback", include_in_schema=False)
async def nowpayments_ipn(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()
    data = await request.json()
    order_id = _safe_int(data.get("order_id"))
    if order_id is None:
        return Response(status_code=400)
    order = await get_shop_order(db, order_id)
    if order is None:
        return Response(status_code=404)
    config = await get_shop_config_by_admin(db, order.admin_id)
    if config is None:
        return Response(status_code=404)
    sig = request.headers.get("x-nowpayments-sig")
    if not verify_nowpayments_signature(config, body, sig):
        return Response(status_code=401)
    status_val = str(data.get("payment_status") or data.get("status") or "").lower()
    if status_val in ("finished", "confirmed", "sending", "paid"):
        await shop_operator.fulfill_paid_order(db, order_id)
    return {"ok": True}


@router.post("/payments/stripe/callback", include_in_schema=False)
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    import json

    body = await request.body()
    try:
        loose = json.loads(body)
    except Exception:
        return Response(status_code=400)
    obj = (loose.get("data") or {}).get("object") or {}
    order_id = _safe_int((obj.get("metadata") or {}).get("order_id") or obj.get("client_reference_id"))
    if order_id is None:
        return Response(status_code=400)
    order = await get_shop_order(db, order_id)
    if order is None:
        return Response(status_code=404)
    config = await get_shop_config_by_admin(db, order.admin_id)
    if config is None:
        return Response(status_code=404)
    try:
        event = verify_stripe_signature(config, body, request.headers.get("Stripe-Signature"))
    except Exception:
        return Response(status_code=401)
    if event.get("type") == "checkout.session.completed":
        await update_shop_order_payment(db, order, payment_paid=True)
        await shop_operator.fulfill_paid_order(db, order_id)
    return {"ok": True}
