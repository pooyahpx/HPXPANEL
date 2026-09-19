from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    Admin,
    AdminRole,
    ShopConfig,
    ShopOrder,
    ShopOrderStatus,
    ShopPlan,
    TelegramProfile,
    TelegramSubDelivery,
    TelegramSupportTicket,
    User,
)


async def _assign_sqlite_pk(db: AsyncSession, model, instance) -> None:
    """Shop tables were created with BIGINT PKs; SQLite only autoincrements INTEGER PKs."""
    bind = await db.connection()
    if bind.dialect.name == "sqlite":
        next_id = (await db.execute(select(func.coalesce(func.max(model.id), 0) + 1))).scalar_one()
        instance.id = int(next_id)


async def get_or_create_telegram_profile(db: AsyncSession, telegram_id: int, lang: str | None = None) -> TelegramProfile:
    profile = await db.get(TelegramProfile, telegram_id)
    if profile is None:
        profile = TelegramProfile(telegram_id=telegram_id, lang=lang or "fa")
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        return profile
    if lang and profile.lang != lang:
        profile.lang = lang
        profile.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(profile)
    return profile


async def get_telegram_lang(db: AsyncSession, telegram_id: int) -> str | None:
    profile = await db.get(TelegramProfile, telegram_id)
    return profile.lang if profile else None


async def set_telegram_lang(db: AsyncSession, telegram_id: int, lang: str) -> TelegramProfile:
    return await get_or_create_telegram_profile(db, telegram_id, lang=lang)


async def mark_join_notified(db: AsyncSession, telegram_id: int) -> bool:
    profile = await get_or_create_telegram_profile(db, telegram_id)
    if profile.join_notified:
        return False
    profile.join_notified = True
    profile.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(profile)
    return True


async def has_test_claimed(db: AsyncSession, telegram_id: int) -> bool:
    profile = await db.get(TelegramProfile, telegram_id)
    return bool(profile and profile.test_claimed)


async def mark_test_claimed(db: AsyncSession, telegram_id: int) -> None:
    profile = await get_or_create_telegram_profile(db, telegram_id)
    profile.test_claimed = True
    profile.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(profile)


async def open_support_ticket(db: AsyncSession, buyer_telegram_id: int) -> TelegramSupportTicket:
    ticket = await db.get(TelegramSupportTicket, buyer_telegram_id)
    if ticket is None:
        ticket = TelegramSupportTicket(buyer_telegram_id=buyer_telegram_id, status="open")
        db.add(ticket)
    else:
        ticket.status = "open"
        ticket.handler_admin_id = None
        ticket.handler_username = None
        ticket.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def get_support_ticket(db: AsyncSession, buyer_telegram_id: int) -> TelegramSupportTicket | None:
    return await db.get(TelegramSupportTicket, buyer_telegram_id)


async def claim_support_ticket(
    db: AsyncSession,
    buyer_telegram_id: int,
    *,
    admin_id: int,
    admin_username: str,
) -> TelegramSupportTicket | None:
    ticket = await db.get(TelegramSupportTicket, buyer_telegram_id)
    if ticket is None or ticket.status != "open":
        return None
    if ticket.handler_admin_id is not None and ticket.handler_admin_id != admin_id:
        return None
    ticket.handler_admin_id = admin_id
    ticket.handler_username = admin_username
    ticket.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def close_support_ticket(
    db: AsyncSession,
    buyer_telegram_id: int,
    *,
    admin_id: int,
    admin_username: str,
) -> TelegramSupportTicket | None:
    ticket = await db.get(TelegramSupportTicket, buyer_telegram_id)
    if ticket is None:
        return None
    ticket.status = "closed"
    ticket.handler_admin_id = admin_id
    ticket.handler_username = admin_username
    ticket.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def support_reply_allowed(db: AsyncSession, buyer_telegram_id: int, admin_id: int) -> tuple[bool, str | None]:
    ticket = await get_support_ticket(db, buyer_telegram_id)
    if ticket is None or ticket.status != "open":
        return False, None
    if ticket.handler_admin_id is not None and ticket.handler_admin_id != admin_id:
        return False, ticket.handler_username
    return True, ticket.handler_username


async def get_owner_admin(db: AsyncSession) -> Admin | None:
    stmt = (
        select(Admin)
        .options(selectinload(Admin.role))
        .join(Admin.role)
        .where(AdminRole.is_owner.is_(True))
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_enabled_shop_config(db: AsyncSession) -> ShopConfig | None:
    stmt = select(ShopConfig).where(ShopConfig.enabled.is_(True)).order_by(ShopConfig.id.asc()).limit(1)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_shop_config_by_admin(db: AsyncSession, admin_id: int) -> ShopConfig | None:
    stmt = select(ShopConfig).where(ShopConfig.admin_id == admin_id).limit(1)
    return (await db.execute(stmt)).scalar_one_or_none()


async def upsert_shop_config(
    db: AsyncSession,
    admin_id: int,
    *,
    enabled: bool | None = None,
    card_number: str | None = None,
    card_holder: str | None = None,
    card_note: str | None = None,
    card_photos: list[str] | None = None,
    welcome_note: str | None = None,
    cards: list[dict[str, str]] | None = None,
    test_enabled: bool | None = None,
    test_data_limit: int | None = None,
    test_expire_days: int | None = None,
    test_group_ids: list[int] | None = None,
    custom_enabled: bool | None = None,
    custom_price_per_gb: int | None = None,
    custom_price_per_day: int | None = None,
    custom_price_per_ip: int | None = None,
    custom_min_gb: int | None = None,
    custom_max_gb: int | None = None,
    custom_min_days: int | None = None,
    custom_max_days: int | None = None,
    custom_base_ip: int | None = None,
    custom_group_ids: list[int] | None = None,
    pay_card_enabled: bool | None = None,
    pay_zarinpal_enabled: bool | None = None,
    pay_zarinpal_merchant_id: str | None = None,
    pay_zarinpal_sandbox: bool | None = None,
    pay_idpay_enabled: bool | None = None,
    pay_idpay_api_key: str | None = None,
    pay_idpay_sandbox: bool | None = None,
    pay_nowpayments_enabled: bool | None = None,
    pay_nowpayments_api_key: str | None = None,
    pay_nowpayments_ipn_secret: str | None = None,
    pay_paypal_enabled: bool | None = None,
    pay_paypal_client_id: str | None = None,
    pay_paypal_client_secret: str | None = None,
    pay_paypal_sandbox: bool | None = None,
    pay_stripe_enabled: bool | None = None,
    pay_stripe_secret_key: str | None = None,
    pay_stripe_webhook_secret: str | None = None,
    pay_callback_base_url: str | None = None,
    pay_fx_toman_per_usd: int | None = None,
    pay_unpaid_expire_minutes: int | None = None,
) -> ShopConfig:
    config = await get_shop_config_by_admin(db, admin_id)
    if config is None:
        config = ShopConfig(admin_id=admin_id)
        await _assign_sqlite_pk(db, ShopConfig, config)
        db.add(config)
    if enabled is not None:
        config.enabled = enabled
    if card_number is not None:
        config.card_number = card_number
    if card_holder is not None:
        config.card_holder = card_holder
    if card_note is not None:
        config.card_note = card_note or None
    if card_photos is not None:
        config.card_photos = card_photos
    if welcome_note is not None:
        config.welcome_note = welcome_note
    if cards is not None:
        config.cards = cards
        if cards:
            config.card_number = cards[0].get("number")
            config.card_holder = cards[0].get("holder") or None
        else:
            config.card_number = None
            config.card_holder = None
    if test_enabled is not None:
        config.test_enabled = test_enabled
    if test_data_limit is not None:
        config.test_data_limit = test_data_limit
    if test_expire_days is not None:
        config.test_expire_days = test_expire_days
    if test_group_ids is not None:
        config.test_group_ids = test_group_ids
    if custom_enabled is not None:
        config.custom_enabled = custom_enabled
    if custom_price_per_gb is not None:
        config.custom_price_per_gb = custom_price_per_gb
    if custom_price_per_day is not None:
        config.custom_price_per_day = custom_price_per_day
    if custom_price_per_ip is not None:
        config.custom_price_per_ip = custom_price_per_ip
    if custom_min_gb is not None:
        config.custom_min_gb = custom_min_gb
    if custom_max_gb is not None:
        config.custom_max_gb = custom_max_gb
    if custom_min_days is not None:
        config.custom_min_days = custom_min_days
    if custom_max_days is not None:
        config.custom_max_days = custom_max_days
    if custom_base_ip is not None:
        config.custom_base_ip = custom_base_ip
    if custom_group_ids is not None:
        config.custom_group_ids = custom_group_ids
    if pay_card_enabled is not None:
        config.pay_card_enabled = pay_card_enabled
    if pay_zarinpal_enabled is not None:
        config.pay_zarinpal_enabled = pay_zarinpal_enabled
    if pay_zarinpal_merchant_id is not None and "••••" not in pay_zarinpal_merchant_id:
        config.pay_zarinpal_merchant_id = pay_zarinpal_merchant_id or None
    if pay_zarinpal_sandbox is not None:
        config.pay_zarinpal_sandbox = pay_zarinpal_sandbox
    if pay_idpay_enabled is not None:
        config.pay_idpay_enabled = pay_idpay_enabled
    if pay_idpay_api_key is not None and "••••" not in pay_idpay_api_key:
        config.pay_idpay_api_key = pay_idpay_api_key or None
    if pay_idpay_sandbox is not None:
        config.pay_idpay_sandbox = pay_idpay_sandbox
    if pay_nowpayments_enabled is not None:
        config.pay_nowpayments_enabled = pay_nowpayments_enabled
    if pay_nowpayments_api_key is not None and "••••" not in pay_nowpayments_api_key:
        config.pay_nowpayments_api_key = pay_nowpayments_api_key or None
    if pay_nowpayments_ipn_secret is not None and "••••" not in pay_nowpayments_ipn_secret:
        config.pay_nowpayments_ipn_secret = pay_nowpayments_ipn_secret or None
    if pay_paypal_enabled is not None:
        config.pay_paypal_enabled = pay_paypal_enabled
    if pay_paypal_client_id is not None and "••••" not in pay_paypal_client_id:
        config.pay_paypal_client_id = pay_paypal_client_id or None
    if pay_paypal_client_secret is not None and "••••" not in pay_paypal_client_secret:
        config.pay_paypal_client_secret = pay_paypal_client_secret or None
    if pay_paypal_sandbox is not None:
        config.pay_paypal_sandbox = pay_paypal_sandbox
    if pay_stripe_enabled is not None:
        config.pay_stripe_enabled = pay_stripe_enabled
    if pay_stripe_secret_key is not None and "••••" not in pay_stripe_secret_key:
        config.pay_stripe_secret_key = pay_stripe_secret_key or None
    if pay_stripe_webhook_secret is not None and "••••" not in pay_stripe_webhook_secret:
        config.pay_stripe_webhook_secret = pay_stripe_webhook_secret or None
    if pay_callback_base_url is not None:
        config.pay_callback_base_url = (pay_callback_base_url or "").strip().rstrip("/") or None
    if pay_fx_toman_per_usd is not None:
        config.pay_fx_toman_per_usd = max(1000, int(pay_fx_toman_per_usd))
    if pay_unpaid_expire_minutes is not None:
        config.pay_unpaid_expire_minutes = max(5, min(10080, int(pay_unpaid_expire_minutes)))
    await db.commit()
    await db.refresh(config)
    return config


async def list_active_plans(db: AsyncSession, admin_id: int) -> list[ShopPlan]:
    stmt = (
        select(ShopPlan)
        .where(ShopPlan.admin_id == admin_id, ShopPlan.is_active.is_(True))
        .order_by(ShopPlan.price_toman.asc(), ShopPlan.id.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def list_plans_for_admin(db: AsyncSession, admin_id: int) -> list[ShopPlan]:
    stmt = select(ShopPlan).where(ShopPlan.admin_id == admin_id).order_by(ShopPlan.id.desc())
    return list((await db.execute(stmt)).scalars().all())


async def get_shop_plan(db: AsyncSession, plan_id: int) -> ShopPlan | None:
    return await db.get(ShopPlan, plan_id)


async def create_shop_plan(
    db: AsyncSession,
    *,
    admin_id: int,
    name: str,
    data_limit: int,
    expire_days: int,
    price_toman: int,
    group_ids: list[int] | None = None,
    ip_limit: int | None = None,
    hwid_limit: int | None = None,
) -> ShopPlan:
    plan = ShopPlan(
        admin_id=admin_id,
        name=name,
        data_limit=data_limit,
        expire_days=expire_days,
        price_toman=price_toman,
        group_ids=group_ids or [],
        ip_limit=ip_limit,
        hwid_limit=hwid_limit,
        is_active=True,
    )
    await _assign_sqlite_pk(db, ShopPlan, plan)
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


async def set_plan_active(db: AsyncSession, plan: ShopPlan, active: bool) -> ShopPlan:
    plan.is_active = active
    await db.commit()
    await db.refresh(plan)
    return plan


async def update_shop_plan(db: AsyncSession, plan: ShopPlan, **fields) -> ShopPlan:
    for key, value in fields.items():
        setattr(plan, key, value)
    await db.commit()
    await db.refresh(plan)
    return plan


async def delete_shop_plan(db: AsyncSession, plan: ShopPlan) -> None:
    await db.delete(plan)
    await db.commit()


async def create_shop_order(
    db: AsyncSession,
    *,
    plan_id: int | None,
    admin_id: int,
    buyer_telegram_id: int,
    buyer_username: str | None,
    receipt_file_id: str | None = None,
    order_kind: str = "purchase",
    renew_user_id: int | None = None,
    requested_username: str | None = None,
    custom_data_gb: int | None = None,
    custom_expire_days: int | None = None,
    custom_ip_limit: int | None = None,
    quoted_price_toman: int | None = None,
    is_custom: bool = False,
    payment_method: str | None = None,
    payment_ref: str | None = None,
    payment_url: str | None = None,
    payment_paid: bool = False,
) -> ShopOrder:
    kind = (order_kind or "purchase").strip().lower()
    if kind not in ("purchase", "renewal"):
        kind = "purchase"
    method = (payment_method or "card").strip().lower() or "card"
    if payment_paid:
        initial_status = ShopOrderStatus.pending
    elif method != "card" and not receipt_file_id:
        initial_status = ShopOrderStatus.awaiting_payment
    else:
        initial_status = ShopOrderStatus.pending
    order = ShopOrder(
        plan_id=plan_id,
        admin_id=admin_id,
        buyer_telegram_id=buyer_telegram_id,
        buyer_username=buyer_username,
        receipt_file_id=receipt_file_id,
        status=initial_status,
        order_kind=kind,
        renew_user_id=renew_user_id if kind == "renewal" else None,
        requested_username=requested_username,
        custom_data_gb=custom_data_gb,
        custom_expire_days=custom_expire_days,
        custom_ip_limit=custom_ip_limit,
        quoted_price_toman=quoted_price_toman,
        is_custom=bool(is_custom),
        payment_method=method,
        payment_ref=payment_ref,
        payment_url=payment_url,
        payment_paid=bool(payment_paid),
    )
    await _assign_sqlite_pk(db, ShopOrder, order)
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


async def update_shop_order_payment(
    db: AsyncSession,
    order: ShopOrder,
    *,
    payment_ref: str | None = None,
    payment_url: str | None = None,
    payment_paid: bool | None = None,
    receipt_file_id: str | None = None,
) -> ShopOrder:
    if payment_ref is not None:
        order.payment_ref = payment_ref
    if payment_url is not None:
        order.payment_url = payment_url
    if payment_paid is not None:
        order.payment_paid = payment_paid
    if receipt_file_id is not None:
        order.receipt_file_id = receipt_file_id
    await db.commit()
    await db.refresh(order)
    return order


async def get_shop_order_by_payment_ref(db: AsyncSession, payment_ref: str) -> ShopOrder | None:
    if not payment_ref:
        return None
    stmt = select(ShopOrder).where(ShopOrder.payment_ref == payment_ref).limit(1)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_shop_order(db: AsyncSession, order_id: int) -> ShopOrder | None:
    return await db.get(ShopOrder, order_id)


async def expire_unpaid_shop_orders(
    db: AsyncSession,
    *,
    admin_id: int | None = None,
    now: datetime | None = None,
) -> int:
    """Mark stale awaiting_payment orders as expired. Returns count expired."""
    from datetime import timedelta as td

    moment = now or datetime.now(UTC)
    configs_stmt = select(ShopConfig)
    if admin_id is not None:
        configs_stmt = configs_stmt.where(ShopConfig.admin_id == admin_id)
    configs = list((await db.execute(configs_stmt)).scalars().all())
    if not configs:
        return 0
    expired_count = 0
    for config in configs:
        minutes = int(getattr(config, "pay_unpaid_expire_minutes", 60) or 60)
        cutoff = moment - td(minutes=max(5, minutes))
        stmt = select(ShopOrder).where(
            ShopOrder.admin_id == config.admin_id,
            ShopOrder.status == ShopOrderStatus.awaiting_payment,
            ShopOrder.payment_paid.is_(False),
            ShopOrder.created_at < cutoff,
        )
        rows = list((await db.execute(stmt)).scalars().all())
        for order in rows:
            order.status = ShopOrderStatus.expired
            expired_count += 1
    if expired_count:
        await db.commit()
    return expired_count


async def list_pending_orders(db: AsyncSession, admin_id: int) -> list[ShopOrder]:
    """Pending orders that need admin review (card receipts / paid leftovers)."""
    await expire_unpaid_shop_orders(db, admin_id=admin_id)
    stmt = (
        select(ShopOrder)
        .where(ShopOrder.admin_id == admin_id, ShopOrder.status == ShopOrderStatus.pending)
        .order_by(ShopOrder.id.asc())
    )
    rows = list((await db.execute(stmt)).scalars().all())
    filtered: list[ShopOrder] = []
    for order in rows:
        method = (getattr(order, "payment_method", None) or "card").lower()
        if method == "card" and order.receipt_file_id or getattr(order, "payment_paid", False):
            filtered.append(order)
    return filtered


async def list_orders_for_admin(
    db: AsyncSession,
    admin_id: int,
    *,
    status: ShopOrderStatus | None = None,
    order_kind: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[ShopOrder], int]:
    filters = [ShopOrder.admin_id == admin_id]
    if status is not None:
        filters.append(ShopOrder.status == status)
    if order_kind:
        filters.append(ShopOrder.order_kind == order_kind)
    base = select(ShopOrder).where(*filters)
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one() or 0)
    stmt = base.order_by(ShopOrder.id.desc()).offset(offset).limit(limit)
    return list((await db.execute(stmt)).scalars().all()), total


async def list_buyer_orders(db: AsyncSession, buyer_telegram_id: int, limit: int = 10) -> list[ShopOrder]:
    stmt = (
        select(ShopOrder)
        .where(ShopOrder.buyer_telegram_id == buyer_telegram_id)
        .order_by(ShopOrder.id.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


async def list_buyer_renewable_accounts(
    db: AsyncSession,
    *,
    buyer_telegram_id: int,
    admin_id: int,
) -> list[tuple[User, ShopOrder]]:
    """Approved purchase/renewal orders for this buyer that still map to an existing panel user."""
    stmt = (
        select(ShopOrder)
        .where(
            ShopOrder.buyer_telegram_id == buyer_telegram_id,
            ShopOrder.admin_id == admin_id,
            ShopOrder.status == ShopOrderStatus.approved,
            ShopOrder.created_user_id.isnot(None),
        )
        .order_by(ShopOrder.id.desc())
    )
    orders = list((await db.execute(stmt)).scalars().all())
    seen: set[int] = set()
    result: list[tuple[User, ShopOrder]] = []
    for order in orders:
        user_id = order.created_user_id
        if user_id is None or user_id in seen:
            continue
        user = await db.get(User, user_id)
        if user is None:
            continue
        seen.add(user_id)
        result.append((user, order))
    return result


async def update_order_status(
    db: AsyncSession,
    order: ShopOrder,
    status: ShopOrderStatus,
    *,
    created_user_id: int | None = None,
    note: str | None = None,
) -> ShopOrder:
    order.status = status
    if created_user_id is not None:
        order.created_user_id = created_user_id
    if note is not None:
        order.note = note
    await db.commit()
    await db.refresh(order)
    return order


async def get_shop_bot_stats(db: AsyncSession, admin_id: int) -> dict[str, int]:
    """Aggregate join / test / order stats for shop admin overview."""
    total_buyers = int((await db.execute(select(func.count()).select_from(TelegramProfile))).scalar_one() or 0)
    joined = int(
        (
            await db.execute(select(func.count()).select_from(TelegramProfile).where(TelegramProfile.join_notified.is_(True)))
        ).scalar_one()
        or 0
    )
    test_claimed = int(
        (
            await db.execute(select(func.count()).select_from(TelegramProfile).where(TelegramProfile.test_claimed.is_(True)))
        ).scalar_one()
        or 0
    )

    test_row = (
        await db.execute(
            select(
                func.count(User.id),
                func.coalesce(func.sum(User.used_traffic), 0),
            ).where(User.note == "shop test config")
        )
    ).one()
    test_accounts = int(test_row[0] or 0)
    test_used_bytes = int(test_row[1] or 0)

    async def _order_count(status: ShopOrderStatus) -> int:
        return int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(ShopOrder)
                    .where(ShopOrder.admin_id == admin_id, ShopOrder.status == status)
                )
            ).scalar_one()
            or 0
        )

    return {
        "total_buyers": total_buyers,
        "joined": joined,
        "test_claimed": test_claimed,
        "test_accounts": test_accounts,
        "test_used_bytes": test_used_bytes,
        "orders_pending": await _order_count(ShopOrderStatus.pending),
        "orders_approved": await _order_count(ShopOrderStatus.approved),
        "orders_rejected": await _order_count(ShopOrderStatus.rejected),
        "orders_renewed": int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(ShopOrder)
                    .where(
                        ShopOrder.admin_id == admin_id,
                        ShopOrder.status == ShopOrderStatus.approved,
                        ShopOrder.order_kind == "renewal",
                    )
                )
            ).scalar_one()
            or 0
        ),
    }


async def get_sub_delivery_by_user_id(db: AsyncSession, user_id: int) -> TelegramSubDelivery | None:
    stmt = select(TelegramSubDelivery).where(TelegramSubDelivery.user_id == user_id).limit(1)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_sub_delivery(db: AsyncSession, delivery_id: int) -> TelegramSubDelivery | None:
    return await db.get(TelegramSubDelivery, delivery_id)


async def upsert_sub_delivery(
    db: AsyncSession,
    *,
    user_id: int,
    buyer_telegram_id: int,
    source_type: str,
    source_id: int | None,
    panel_username: str,
    sub_version: str,
) -> TelegramSubDelivery:
    delivery = await get_sub_delivery_by_user_id(db, user_id)
    if delivery is None:
        delivery = TelegramSubDelivery(
            user_id=user_id,
            buyer_telegram_id=buyer_telegram_id,
            source_type=source_type,
            source_id=source_id,
            panel_username=panel_username,
            sub_version=sub_version,
        )
        db.add(delivery)
    else:
        delivery.buyer_telegram_id = buyer_telegram_id
        delivery.source_type = source_type
        delivery.source_id = source_id
        delivery.panel_username = panel_username
        delivery.sub_version = sub_version
        delivery.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(delivery)
    return delivery


async def update_sub_delivery_version(db: AsyncSession, delivery: TelegramSubDelivery, sub_version: str) -> TelegramSubDelivery:
    delivery.sub_version = sub_version
    delivery.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(delivery)
    return delivery


async def list_sub_deliveries(db: AsyncSession, *, offset: int = 0, limit: int = 10) -> tuple[list[TelegramSubDelivery], int]:
    total = int((await db.execute(select(func.count()).select_from(TelegramSubDelivery))).scalar_one() or 0)
    stmt = (
        select(TelegramSubDelivery)
        .order_by(TelegramSubDelivery.id.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    return rows, total


async def list_sub_deliveries_for_check(db: AsyncSession) -> list[TelegramSubDelivery]:
    stmt = select(TelegramSubDelivery).order_by(TelegramSubDelivery.id.asc())
    return list((await db.execute(stmt)).scalars().all())


async def list_approved_orders(
    db: AsyncSession, *, offset: int = 0, limit: int = 10
) -> tuple[list[ShopOrder], int]:
    base = select(ShopOrder).where(
        ShopOrder.status == ShopOrderStatus.approved,
        ShopOrder.created_user_id.isnot(None),
    )
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one() or 0)
    stmt = base.order_by(ShopOrder.id.desc()).offset(offset).limit(limit)
    return list((await db.execute(stmt)).scalars().all()), total
