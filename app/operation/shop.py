from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime as dt, timedelta as td

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
    get_shop_plan,
    get_telegram_lang,
    list_orders_for_admin,
    list_plans_for_admin,
    update_order_status,
    update_shop_plan,
    upsert_shop_config,
)
from app.db.crud.user import get_user_by_id
from app.db.models import ShopOrder, ShopOrderStatus, ShopPlan, UserStatus
from app.models.admin import AdminDetails
from app.models.shop import (
    ShopApproveResponse,
    ShopCard,
    ShopConfigResponse,
    ShopConfigUpdate,
    ShopOrderListResponse,
    ShopOrderResponse,
    ShopPlanCreate,
    ShopPlanResponse,
    ShopPlanUpdate,
    ShopStatsResponse,
)
from app.models.user import UserCreate
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
        created_at=config.created_at,
    )


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
    plan = await get_shop_plan(db, order.plan_id)
    created_username = None
    if order.created_user_id:
        user = await get_user_by_id(db, order.created_user_id, load_admin=False, load_next_plan=False, load_usage_logs=False, load_groups=False)
        created_username = user.username if user else None
    return ShopOrderResponse(
        id=order.id,
        plan_id=order.plan_id,
        admin_id=order.admin_id,
        buyer_telegram_id=order.buyer_telegram_id,
        buyer_username=order.buyer_username,
        status=order.status,
        receipt_file_id=order.receipt_file_id,
        created_user_id=order.created_user_id,
        created_username=created_username,
        plan_name=plan.name if plan else None,
        plan_price_toman=int(plan.price_toman) if plan else None,
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
        offset: int = 0,
        limit: int = 50,
    ) -> ShopOrderListResponse:
        shop_admin = await self._resolve_shop_admin(db, admin)
        orders, total = await list_orders_for_admin(db, shop_admin.id, status=status, offset=offset, limit=limit)
        return ShopOrderListResponse(
            orders=[await _order_response(db, order) for order in orders],
            total=total,
        )

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

        plan = await get_shop_plan(db, order.plan_id)
        if plan is None:
            await self.raise_error("Plan not found", 404, db)

        username = f"tg{order.buyer_telegram_id}_{secrets.token_hex(2)}"
        expire = None
        if plan.expire_days and plan.expire_days > 0:
            expire = dt.now(UTC) + td(days=plan.expire_days)

        try:
            new_user = UserCreate(
                username=username,
                status=UserStatus.active,
                data_limit=plan.data_limit or None,
                expire=expire,
                group_ids=list(plan.group_ids or []),
                ip_limit=plan.ip_limit,
                hwid_limit=plan.hwid_limit,
                note=f"shop order #{order.id}",
            )
            user = await self.user_operator.create_user(db, new_user, shop_admin, skip_role_limits=True)
        except Exception as exc:
            await self.raise_error(str(exc)[:180], 400, db)

        order = await update_order_status(db, order, ShopOrderStatus.approved, created_user_id=user.id)
        await self._notify_buyer_approved(db, shop_admin, order, plan, user)
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

    async def _notify_buyer_approved(self, db: AsyncSession, admin: AdminDetails, order: ShopOrder, plan: ShopPlan, user) -> None:
        try:
            from app.telegram import get_bot
            from app.telegram.utils.i18n import rich
            from app.telegram.utils.shop_helpers import notify_owner_order_approved
            from app.telegram.utils.sub_delivery import record_sub_delivery

            await get_or_create_telegram_profile(db, order.buyer_telegram_id)
            buyer_lang = (await get_telegram_lang(db, order.buyer_telegram_id)) or "fa"
            bot = get_bot()
            if bot:
                text = rich(
                    buyer_lang,
                    "order_approved",
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

                await notify_owner_order_approved(
                    db=db,
                    bot=bot,
                    approver=admin,
                    order_id=order.id,
                    buyer_label=order.buyer_username or str(order.buyer_telegram_id),
                    plan_name=plan.name,
                    username=user.username,
                )

            await record_sub_delivery(
                db,
                user_id=user.id,
                buyer_telegram_id=order.buyer_telegram_id,
                source_type="order",
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
