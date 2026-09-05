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
    plan_id: int,
    admin_id: int,
    buyer_telegram_id: int,
    buyer_username: str | None,
    receipt_file_id: str,
) -> ShopOrder:
    order = ShopOrder(
        plan_id=plan_id,
        admin_id=admin_id,
        buyer_telegram_id=buyer_telegram_id,
        buyer_username=buyer_username,
        receipt_file_id=receipt_file_id,
        status=ShopOrderStatus.pending,
    )
    await _assign_sqlite_pk(db, ShopOrder, order)
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


async def get_shop_order(db: AsyncSession, order_id: int) -> ShopOrder | None:
    return await db.get(ShopOrder, order_id)


async def list_pending_orders(db: AsyncSession, admin_id: int) -> list[ShopOrder]:
    stmt = (
        select(ShopOrder)
        .where(ShopOrder.admin_id == admin_id, ShopOrder.status == ShopOrderStatus.pending)
        .order_by(ShopOrder.id.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def list_orders_for_admin(
    db: AsyncSession,
    admin_id: int,
    *,
    status: ShopOrderStatus | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[ShopOrder], int]:
    filters = [ShopOrder.admin_id == admin_id]
    if status is not None:
        filters.append(ShopOrder.status == status)
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
