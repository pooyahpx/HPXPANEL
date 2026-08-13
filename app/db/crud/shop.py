from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Admin, AdminRole, ShopConfig, ShopOrder, ShopOrderStatus, ShopPlan, TelegramProfile


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
) -> ShopConfig:
    config = await get_shop_config_by_admin(db, admin_id)
    if config is None:
        config = ShopConfig(admin_id=admin_id)
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
