from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime as dt, timedelta as td

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud.admin import build_admin_details, get_admin_by_id
from app.db.crud.shop import (
    create_shop_plan,
    delete_shop_plan,
    get_or_create_telegram_profile,
    get_owner_admin,
    get_shop_bot_stats,
    get_shop_config_by_admin,
    get_shop_order,
    get_shop_order_by_payment_ref,
    get_shop_plan,
    get_telegram_lang,
    list_orders_for_admin,
    list_plans_for_admin,
    update_order_status,
    update_shop_order_payment,
    update_shop_plan,
    upsert_shop_config,
)
from app.db.crud.user import get_user_by_id
from app.db.models import ShopOrder, ShopOrderStatus, ShopPlan, UserStatus
from app.models.admin import AdminDetails
from app.models.shop import (
    CreateBudgetLedgerEntry,
    CreateBudgetLedgerListResponse,
    ShopApproveResponse,
    ShopCard,
    ShopConfigResponse,
    ShopConfigUpdate,
    ShopOrderKindLiteral,
    ShopOrderListResponse,
    ShopOrderResponse,
    ShopPlanCreate,
    ShopPlanResponse,
    ShopPlanUpdate,
    ShopStatsResponse,
)
from app.models.user import UserCreate, UserModify
from app.operation import BaseOperation, OperatorType
from app.operation.user import UserOperation

logger = logging.getLogger(__name__)


def _normalize_cards(cards: list[ShopCard] | list[dict] | None) -> list[dict[str, str]]:
    if not cards:
        return []
    normalized: list[dict[str, str]] = []
    for card in cards:
        if isinstance(card, ShopCard):
            number = card.number.strip()
            holder = (card.holder or "").strip()
        else:
            number = str(card.get("number") or "").strip()
            holder = str(card.get("holder") or "").strip()
        if not number:
            continue
        normalized.append({"number": number, "holder": holder})
    return normalized


def _config_response(config) -> ShopConfigResponse:
    raw_cards = config.cards or []
    cards: list[ShopCard] = []
    for item in raw_cards:
        if isinstance(item, dict) and item.get("number"):
            cards.append(ShopCard(number=str(item["number"]), holder=str(item.get("holder") or "")))
    if not cards and config.card_number:
        cards.append(ShopCard(number=config.card_number, holder=config.card_holder or ""))
    return ShopConfigResponse(
        id=config.id,
        admin_id=config.admin_id,
        enabled=bool(config.enabled),
        card_number=config.card_number,
        card_holder=config.card_holder,
        card_note=config.card_note,
        card_photos=list(config.card_photos or []),
        welcome_note=config.welcome_note,
        cards=cards,
        test_enabled=bool(config.test_enabled),
        test_data_limit=int(config.test_data_limit or 0),
        test_expire_days=int(config.test_expire_days or 0),
        test_group_ids=list(config.test_group_ids or []),
        custom_enabled=bool(getattr(config, "custom_enabled", False)),
        custom_price_per_gb=int(getattr(config, "custom_price_per_gb", 0) or 0),
        custom_price_per_day=int(getattr(config, "custom_price_per_day", 0) or 0),
        custom_price_per_ip=int(getattr(config, "custom_price_per_ip", 0) or 0),
        custom_min_gb=int(getattr(config, "custom_min_gb", 1) or 1),
        custom_max_gb=int(getattr(config, "custom_max_gb", 500) or 500),
        custom_min_days=int(getattr(config, "custom_min_days", 1) or 1),
        custom_max_days=int(getattr(config, "custom_max_days", 365) or 365),
        custom_base_ip=int(getattr(config, "custom_base_ip", 1) or 1),
        custom_group_ids=list(getattr(config, "custom_group_ids", None) or []),
        pay_card_enabled=bool(getattr(config, "pay_card_enabled", True)),
        pay_zarinpal_enabled=bool(getattr(config, "pay_zarinpal_enabled", False)),
        pay_zarinpal_merchant_id=getattr(config, "pay_zarinpal_merchant_id", None),
        pay_zarinpal_sandbox=bool(getattr(config, "pay_zarinpal_sandbox", False)),
        pay_idpay_enabled=bool(getattr(config, "pay_idpay_enabled", False)),
        pay_idpay_api_key=_mask_cfg(getattr(config, "pay_idpay_api_key", None)),
        pay_idpay_sandbox=bool(getattr(config, "pay_idpay_sandbox", True)),
        pay_nowpayments_enabled=bool(getattr(config, "pay_nowpayments_enabled", False)),
        pay_nowpayments_api_key=_mask_cfg(getattr(config, "pay_nowpayments_api_key", None)),
        pay_nowpayments_ipn_secret=_mask_cfg(getattr(config, "pay_nowpayments_ipn_secret", None)),
        pay_paypal_enabled=bool(getattr(config, "pay_paypal_enabled", False)),
        pay_paypal_client_id=getattr(config, "pay_paypal_client_id", None),
        pay_paypal_client_secret=_mask_cfg(getattr(config, "pay_paypal_client_secret", None)),
        pay_paypal_sandbox=bool(getattr(config, "pay_paypal_sandbox", True)),
        pay_stripe_enabled=bool(getattr(config, "pay_stripe_enabled", False)),
        pay_stripe_secret_key=_mask_cfg(getattr(config, "pay_stripe_secret_key", None)),
        pay_stripe_webhook_secret=_mask_cfg(getattr(config, "pay_stripe_webhook_secret", None)),
        pay_callback_base_url=getattr(config, "pay_callback_base_url", None),
        enabled_gateways=_enabled_gateways(config),
        created_at=config.created_at,
    )


def _mask_cfg(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "••••"
    return f"{value[:4]}••••{value[-4:]}"


def _enabled_gateways(config) -> list[str]:
    from app.shop.payments import enabled_gateways

    return enabled_gateways(config)


def _plan_response(plan: ShopPlan) -> ShopPlanResponse:
    return ShopPlanResponse(
        id=plan.id,
        admin_id=plan.admin_id,
        name=plan.name,
        data_limit=int(plan.data_limit or 0),
        expire_days=int(plan.expire_days or 0),
        price_toman=int(plan.price_toman or 0),
        group_ids=list(plan.group_ids or []),
        ip_limit=plan.ip_limit,
        hwid_limit=plan.hwid_limit,
        is_active=bool(plan.is_active),
        created_at=plan.created_at,
    )


async def _order_response(db: AsyncSession, order: ShopOrder) -> ShopOrderResponse:
    plan = await get_shop_plan(db, order.plan_id) if order.plan_id else None
    created_username = None
    if order.created_user_id:
        user = await get_user_by_id(db, order.created_user_id, load_admin=False, load_next_plan=False, load_usage_logs=False, load_groups=False)
        created_username = user.username if user else None
    renew_username = None
    renew_user_id = getattr(order, "renew_user_id", None)
    if renew_user_id:
        renew_user = await get_user_by_id(
            db, renew_user_id, load_admin=False, load_next_plan=False, load_usage_logs=False, load_groups=False
        )
        renew_username = renew_user.username if renew_user else None
    kind_raw = getattr(order, "order_kind", None) or "purchase"
    try:
        order_kind = ShopOrderKindLiteral(kind_raw)
    except ValueError:
        order_kind = ShopOrderKindLiteral.purchase
    return ShopOrderResponse(
        id=order.id,
        plan_id=order.plan_id,
        admin_id=order.admin_id,
        buyer_telegram_id=order.buyer_telegram_id,
        buyer_username=order.buyer_username,
        status=order.status,
        order_kind=order_kind,
        renew_user_id=renew_user_id,
        renew_username=renew_username,
        receipt_file_id=order.receipt_file_id,
        has_receipt=bool(order.receipt_file_id),
        created_user_id=order.created_user_id,
        created_username=created_username,
        plan_name=plan.name if plan else ("Custom" if getattr(order, "is_custom", False) else None),
        plan_price_toman=(
            int(order.quoted_price_toman)
            if getattr(order, "quoted_price_toman", None) is not None
            else (int(plan.price_toman) if plan else None)
        ),
        requested_username=getattr(order, "requested_username", None),
        custom_data_gb=getattr(order, "custom_data_gb", None),
        custom_expire_days=getattr(order, "custom_expire_days", None),
        custom_ip_limit=getattr(order, "custom_ip_limit", None),
        quoted_price_toman=getattr(order, "quoted_price_toman", None),
        is_custom=bool(getattr(order, "is_custom", False)),
        payment_method=getattr(order, "payment_method", None),
        payment_ref=getattr(order, "payment_ref", None),
        payment_url=getattr(order, "payment_url", None),
        payment_paid=bool(getattr(order, "payment_paid", False)),
        note=order.note,
        created_at=order.created_at,
    )


class ShopOperation(BaseOperation):
    def __init__(self, operator_type: OperatorType = OperatorType.API):
        super().__init__(operator_type)
        self.user_operator = UserOperation(operator_type)

    async def _resolve_shop_admin(self, db: AsyncSession, admin: AdminDetails) -> AdminDetails:
        """Env/sudoer tokens have no DB id; bind shop rows to the owner admin record."""
        if admin.id is not None:
            db_admin = await get_admin_by_id(db, admin.id, load_users=False, load_usage_logs=False)
            if db_admin is not None:
                return build_admin_details(db_admin, include_loaded_metrics=False)
        owner = await get_owner_admin(db)
        if owner is None:
            await self.raise_error("Owner admin not found for shop", 400, db)
        return build_admin_details(owner, include_loaded_metrics=False)

    async def get_config(self, db: AsyncSession, admin: AdminDetails) -> ShopConfigResponse:
        shop_admin = await self._resolve_shop_admin(db, admin)
        config = await get_shop_config_by_admin(db, shop_admin.id)
        if config is None:
            config = await upsert_shop_config(db, shop_admin.id, enabled=False)
        return _config_response(config)

    async def update_config(self, db: AsyncSession, admin: AdminDetails, payload: ShopConfigUpdate) -> ShopConfigResponse:
        shop_admin = await self._resolve_shop_admin(db, admin)
        kwargs = payload.model_dump(exclude_unset=True)
        if "cards" in kwargs and kwargs["cards"] is not None:
            kwargs["cards"] = _normalize_cards(kwargs["cards"])

        existing = await get_shop_config_by_admin(db, shop_admin.id)
        will_enable_custom = kwargs.get("custom_enabled")
        if will_enable_custom is None and existing is not None:
            will_enable_custom = bool(existing.custom_enabled)
        if will_enable_custom:
            groups = kwargs.get("custom_group_ids")
            if groups is None and existing is not None:
                groups = list(existing.custom_group_ids or [])
            if not groups:
                await self.raise_error("you must select at least one group for custom purchase", 400, db)

        config = await upsert_shop_config(db, shop_admin.id, **kwargs)
        return _config_response(config)

    async def list_plans(self, db: AsyncSession, admin: AdminDetails) -> list[ShopPlanResponse]:
        shop_admin = await self._resolve_shop_admin(db, admin)
        plans = await list_plans_for_admin(db, shop_admin.id)
        return [_plan_response(plan) for plan in plans]

    async def create_plan(self, db: AsyncSession, admin: AdminDetails, payload: ShopPlanCreate) -> ShopPlanResponse:
        shop_admin = await self._resolve_shop_admin(db, admin)
        plan = await create_shop_plan(
            db,
            admin_id=shop_admin.id,
            name=payload.name.strip(),
            data_limit=payload.data_limit,
            expire_days=payload.expire_days,
            price_toman=payload.price_toman,
            group_ids=payload.group_ids,
            ip_limit=payload.ip_limit,
            hwid_limit=payload.hwid_limit,
        )
        if payload.is_active is False:
            plan = await update_shop_plan(db, plan, is_active=False)
        return _plan_response(plan)

    async def update_plan(self, db: AsyncSession, admin: AdminDetails, plan_id: int, payload: ShopPlanUpdate) -> ShopPlanResponse:
        shop_admin = await self._resolve_shop_admin(db, admin)
        plan = await get_shop_plan(db, plan_id)
        if plan is None or plan.admin_id != shop_admin.id:
            await self.raise_error("Plan not found", 404, db)
        fields = payload.model_dump(exclude_unset=True)
        if "name" in fields and fields["name"] is not None:
            fields["name"] = fields["name"].strip()
        plan = await update_shop_plan(db, plan, **fields)
        return _plan_response(plan)

    async def delete_plan(self, db: AsyncSession, admin: AdminDetails, plan_id: int) -> None:
        shop_admin = await self._resolve_shop_admin(db, admin)
        plan = await get_shop_plan(db, plan_id)
        if plan is None or plan.admin_id != shop_admin.id:
            await self.raise_error("Plan not found", 404, db)
        await delete_shop_plan(db, plan)

    async def list_orders(
        self,
        db: AsyncSession,
        admin: AdminDetails,
        *,
        status: ShopOrderStatus | None = None,
        order_kind: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> ShopOrderListResponse:
        shop_admin = await self._resolve_shop_admin(db, admin)
        orders, total = await list_orders_for_admin(
            db, shop_admin.id, status=status, order_kind=order_kind, offset=offset, limit=limit
        )
        return ShopOrderListResponse(
            orders=[await _order_response(db, order) for order in orders],
            total=total,
        )

    async def get_order_receipt(self, db: AsyncSession, admin: AdminDetails, order_id: int) -> tuple[bytes, str]:
        """Fetch the card-to-card receipt image from Telegram for the panel UI."""
        import io
        import mimetypes
        from pathlib import Path

        from aiogram import Bot

        from app.settings import telegram_settings
        from app.telegram import get_bot

        shop_admin = await self._resolve_shop_admin(db, admin)
        order = await get_shop_order(db, order_id)
        if order is None or order.admin_id != shop_admin.id:
            await self.raise_error("Order not found", 404, db)
        if not order.receipt_file_id:
            await self.raise_error("Receipt not found", 404, db)

        bot = get_bot()
        owned = False
        if bot is None:
            settings = await telegram_settings()
            if not settings.token:
                await self.raise_error("Telegram bot is not configured", 503, db)
            bot = Bot(token=settings.token)
            owned = True

        try:
            file = await bot.get_file(order.receipt_file_id)
            if not file.file_path:
                await self.raise_error("Receipt file unavailable", 502, db)
            buf = io.BytesIO()
            await bot.download_file(file.file_path, destination=buf)
            content = buf.getvalue()
            if not content:
                await self.raise_error("Receipt file empty", 502, db)
            media_type = mimetypes.guess_type(Path(file.file_path).name)[0] or "image/jpeg"
            return content, media_type
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Failed to fetch shop receipt for order %s: %s", order_id, exc)
            await self.raise_error("Could not download receipt from Telegram", 502, db)
            raise  # pragma: no cover
        finally:
            if owned:
                await bot.session.close()

    async def get_stats(self, db: AsyncSession, admin: AdminDetails) -> ShopStatsResponse:
        shop_admin = await self._resolve_shop_admin(db, admin)
        stats = await get_shop_bot_stats(db, shop_admin.id)
        return ShopStatsResponse(**stats)

    async def approve_order(self, db: AsyncSession, admin: AdminDetails, order_id: int) -> ShopApproveResponse:
        shop_admin = await self._resolve_shop_admin(db, admin)
        order = await get_shop_order(db, order_id)
        if order is None or order.admin_id != shop_admin.id:
            await self.raise_error("Order not found", 404, db)
        if order.status != ShopOrderStatus.pending:
            await self.raise_error("Order is not pending", 400, db)

        plan = await get_shop_plan(db, order.plan_id) if order.plan_id else None
        if not getattr(order, "is_custom", False) and plan is None:
            await self.raise_error("Plan not found", 404, db)

        order_kind = (getattr(order, "order_kind", None) or "purchase").lower()
        if order_kind == "renewal" or order.renew_user_id:
            if plan is None:
                await self.raise_error("Plan not found", 404, db)
            return await self._approve_renewal_order(db, shop_admin, order, plan)
        return await self._approve_purchase_order(db, shop_admin, order, plan)

    async def fulfill_paid_order(self, db: AsyncSession, order_id: int) -> ShopApproveResponse | None:
        """Mark online payment as paid and auto-approve. Idempotent if already approved."""
        order = await get_shop_order(db, order_id)
        if order is None:
            return None
        if order.status == ShopOrderStatus.approved:
            return None
        if order.status != ShopOrderStatus.pending:
            return None
        if not getattr(order, "payment_paid", False):
            await update_shop_order_payment(db, order, payment_paid=True)
            order = await get_shop_order(db, order_id)
        db_admin = await get_admin_by_id(db, order.admin_id, load_users=False, load_usage_logs=False)
        if db_admin is None:
            logger.error("Shop order %s admin %s missing for auto-approve", order_id, order.admin_id)
            return None
        admin = build_admin_details(db_admin, include_loaded_metrics=False)
        return await self.approve_order(db, admin, order_id)

    async def fulfill_by_payment_ref(self, db: AsyncSession, payment_ref: str) -> ShopApproveResponse | None:
        order = await get_shop_order_by_payment_ref(db, payment_ref)
        if order is None:
            return None
        return await self.fulfill_paid_order(db, order.id)

    async def _approve_purchase_order(
        self, db: AsyncSession, shop_admin: AdminDetails, order: ShopOrder, plan: ShopPlan | None
    ) -> ShopApproveResponse:
        requested = (getattr(order, "requested_username", None) or "").strip() or None
        username = requested or f"tg{order.buyer_telegram_id}_{secrets.token_hex(2)}"

        is_custom = bool(getattr(order, "is_custom", False))
        if is_custom:
            config = await get_shop_config_by_admin(db, shop_admin.id)
            group_ids = list((config.custom_group_ids if config else None) or [])
            if not group_ids:
                await self.raise_error("Custom purchase groups are not configured", 400, db)
            gb = int(order.custom_data_gb or 0)
            days = int(order.custom_expire_days or 0)
            data_limit = gb * (1024**3) if gb > 0 else None
            expire = dt.now(UTC) + td(days=days) if days > 0 else None
            ip_limit = order.custom_ip_limit
            hwid_limit = None
        else:
            assert plan is not None
            group_ids = list(plan.group_ids or [])
            data_limit = plan.data_limit or None
            expire = None
            if plan.expire_days and plan.expire_days > 0:
                expire = dt.now(UTC) + td(days=plan.expire_days)
            ip_limit = plan.ip_limit
            hwid_limit = plan.hwid_limit

        try:
            new_user = UserCreate(
                username=username,
                status=UserStatus.active,
                data_limit=data_limit,
                expire=expire,
                group_ids=group_ids,
                ip_limit=ip_limit,
                hwid_limit=hwid_limit,
                note=f"shop order #{order.id}",
            )
            user = await self.user_operator.create_user(db, new_user, shop_admin, skip_role_limits=True)
        except Exception as exc:
            await self.raise_error(str(exc)[:180], 400, db)

        order = await update_order_status(db, order, ShopOrderStatus.approved, created_user_id=user.id)
        await self._notify_buyer_approved(db, shop_admin, order, plan, user, renewal=False)
        return ShopApproveResponse(
            order=await _order_response(db, order),
            username=user.username,
            subscription_url=getattr(user, "subscription_url", None),
        )

    async def _approve_renewal_order(
        self, db: AsyncSession, shop_admin: AdminDetails, order: ShopOrder, plan: ShopPlan
    ) -> ShopApproveResponse:
        user_id = order.renew_user_id or order.created_user_id
        if not user_id:
            await self.raise_error("Renewal target user missing", 400, db)

        db_user = await get_user_by_id(
            db, int(user_id), load_admin=True, load_next_plan=True, load_usage_logs=True, load_groups=True
        )
        if db_user is None:
            await self.raise_error("User to renew not found", 404, db)

        expire = None
        if plan.expire_days and plan.expire_days > 0:
            expire = dt.now(UTC) + td(days=plan.expire_days)

        modify = UserModify(
            status=UserStatus.active,
            data_limit=int(plan.data_limit or 0),
            expire=expire,
            group_ids=list(plan.group_ids or []) or None,
            ip_limit=plan.ip_limit,
            hwid_limit=plan.hwid_limit,
            note=f"shop renewal #{order.id}",
        )
        try:
            user = await self.user_operator._modify_user(db, db_user, modify, shop_admin, skip_role_limits=True)
            # Re-load after modify for reset (include next_plan — reset deletes it safely)
            db_user = await get_user_by_id(
                db, int(user_id), load_admin=True, load_next_plan=True, load_usage_logs=True, load_groups=True
            )
            if db_user is not None:
                user = await self.user_operator._reset_user_data_usage(
                    db, db_user, shop_admin, emit_status_change_notification=False
                )
        except Exception as exc:
            await self.raise_error(str(exc)[:180], 400, db)

        order = await update_order_status(db, order, ShopOrderStatus.approved, created_user_id=user.id)
        await self._notify_buyer_approved(db, shop_admin, order, plan, user, renewal=True)
        return ShopApproveResponse(
            order=await _order_response(db, order),
            username=user.username,
            subscription_url=getattr(user, "subscription_url", None),
        )

    async def reject_order(
        self,
        db: AsyncSession,
        admin: AdminDetails,
        order_id: int,
        *,
        note: str | None = None,
    ) -> ShopOrderResponse:
        shop_admin = await self._resolve_shop_admin(db, admin)
        order = await get_shop_order(db, order_id)
        if order is None or order.admin_id != shop_admin.id:
            await self.raise_error("Order not found", 404, db)
        if order.status != ShopOrderStatus.pending:
            await self.raise_error("Order is not pending", 400, db)

        order = await update_order_status(db, order, ShopOrderStatus.rejected, note=note)
        await self._notify_buyer_rejected(db, order)
        return await _order_response(db, order)

    async def _notify_buyer_approved(
        self, db: AsyncSession, admin: AdminDetails, order: ShopOrder, plan: ShopPlan | None, user, *, renewal: bool = False
    ) -> None:
        try:
            from app.telegram import get_bot
            from app.telegram.utils.i18n import rich
            from app.telegram.utils.shop_helpers import notify_owner_order_approved
            from app.telegram.utils.sub_delivery import record_sub_delivery

            await get_or_create_telegram_profile(db, order.buyer_telegram_id)
            buyer_lang = (await get_telegram_lang(db, order.buyer_telegram_id)) or "fa"
            bot = get_bot()
            if bot:
                msg_key = "order_renewed" if renewal else "order_approved"
                text = rich(
                    buyer_lang,
                    msg_key,
                    id=order.id,
                    username=user.username,
                    url=user.subscription_url,
                )
                try:
                    await bot.send_message(order.buyer_telegram_id, text)
                    from app.telegram.utils.qr import subscription_qr_file

                    await bot.send_photo(order.buyer_telegram_id, subscription_qr_file(user.subscription_url, user.username))
                except Exception:
                    try:
                        await bot.send_message(order.buyer_telegram_id, text)
                    except Exception:
                        logger.debug("Failed to notify shop buyer %s", order.buyer_telegram_id, exc_info=True)

                plan_name = plan.name if plan else ("Custom" if getattr(order, "is_custom", False) else "?")
                await notify_owner_order_approved(
                    db=db,
                    bot=bot,
                    approver=admin,
                    order_id=order.id,
                    buyer_label=order.buyer_username or str(order.buyer_telegram_id),
                    plan_name=plan_name,
                    username=user.username,
                    renewal=renewal,
                )

            await record_sub_delivery(
                db,
                user_id=user.id,
                buyer_telegram_id=order.buyer_telegram_id,
                source_type="renewal" if renewal else "order",
                source_id=order.id,
                panel_username=user.username,
            )
        except Exception:
            logger.debug("Shop approve side-effects failed for order %s", order.id, exc_info=True)

    async def _notify_buyer_rejected(self, db: AsyncSession, order: ShopOrder) -> None:
        try:
            from app.telegram import get_bot
            from app.telegram.utils.i18n import t

            bot = get_bot()
            if not bot:
                return
            buyer_lang = (await get_telegram_lang(db, order.buyer_telegram_id)) or "fa"
            await bot.send_message(order.buyer_telegram_id, t(buyer_lang, "order_rejected", id=order.id))
        except Exception:
            logger.debug("Failed to notify rejected shop buyer %s", order.buyer_telegram_id, exc_info=True)

    async def list_create_budget_accounting(
        self,
        db: AsyncSession,
        admin: AdminDetails,
        *,
        admin_id: int | None = None,
        settled: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> CreateBudgetLedgerListResponse:
        from app.db.crud.create_budget_ledger import get_admin_usernames_map, list_create_budget_ledger

        # Owner sees all (optional filter). Non-owner only their own ledger.
        if admin.is_owner:
            target_admin_id = admin_id
        else:
            if admin.id is None:
                raise HTTPException(status_code=403, detail="Admin id required")
            if admin_id is not None and int(admin_id) != int(admin.id):
                raise HTTPException(status_code=403, detail="Not allowed to view other admins")
            target_admin_id = int(admin.id)

        rows, total = await list_create_budget_ledger(
            db, admin_id=target_admin_id, settled=settled, offset=offset, limit=limit
        )
        names = await get_admin_usernames_map(db, {int(r.admin_id) for r in rows})
        entries = [
            CreateBudgetLedgerEntry(
                id=r.id,
                admin_id=r.admin_id,
                admin_username=names.get(int(r.admin_id)),
                entry_type=r.entry_type,
                amount_toman=r.amount_toman,
                balance_after=r.balance_after,
                actor_admin_id=r.actor_admin_id,
                user_id=r.user_id,
                username=r.username,
                billable_gb=r.billable_gb,
                billable_days=r.billable_days,
                price_per_gb=r.price_per_gb,
                price_per_day=r.price_per_day,
                pricing_mode=r.pricing_mode,
                tier_gb=r.tier_gb,
                detail=r.detail,
                settled_with_owner=bool(getattr(r, "settled_with_owner", False)),
                settled_at=getattr(r, "settled_at", None),
                settled_by_admin_id=getattr(r, "settled_by_admin_id", None),
                created_at=r.created_at,
            )
            for r in rows
        ]
        return CreateBudgetLedgerListResponse(entries=entries, total=total)

    async def settle_create_budget_entry(
        self,
        db: AsyncSession,
        admin: AdminDetails,
        entry_id: int,
        *,
        settled: bool = True,
    ) -> CreateBudgetLedgerEntry:
        from app.db.crud.create_budget_ledger import (
            get_admin_usernames_map,
            get_create_budget_ledger_entry,
            set_create_budget_ledger_settled,
        )

        if not admin.is_owner:
            raise HTTPException(status_code=403, detail="Only owner can settle budget ledger entries")

        entry = await get_create_budget_ledger_entry(db, entry_id)
        if entry is None:
            await self.raise_error("Ledger entry not found", 404, db)

        entry = await set_create_budget_ledger_settled(
            db,
            entry,
            settled=settled,
            settled_by_admin_id=admin.id,
        )
        names = await get_admin_usernames_map(db, {int(entry.admin_id)})
        return CreateBudgetLedgerEntry(
            id=entry.id,
            admin_id=entry.admin_id,
            admin_username=names.get(int(entry.admin_id)),
            entry_type=entry.entry_type,
            amount_toman=entry.amount_toman,
            balance_after=entry.balance_after,
            actor_admin_id=entry.actor_admin_id,
            user_id=entry.user_id,
            username=entry.username,
            billable_gb=entry.billable_gb,
            billable_days=entry.billable_days,
            price_per_gb=entry.price_per_gb,
            price_per_day=entry.price_per_day,
            pricing_mode=entry.pricing_mode,
            tier_gb=entry.tier_gb,
            detail=entry.detail,
            settled_with_owner=bool(entry.settled_with_owner),
            settled_at=entry.settled_at,
            settled_by_admin_id=entry.settled_by_admin_id,
            created_at=entry.created_at,
        )
