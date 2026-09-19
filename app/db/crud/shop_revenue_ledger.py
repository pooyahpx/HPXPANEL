"""CRUD for shop gateway revenue ledger (paid order sales)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ShopRevenueLedger


async def record_shop_sale(
    db: AsyncSession,
    *,
    admin_id: int,
    order_id: int,
    amount_toman: int,
    payment_method: str | None,
    payment_ref: str | None = None,
    buyer_telegram_id: int | None = None,
    username: str | None = None,
    detail: str | None = None,
    commit: bool = True,
) -> ShopRevenueLedger | None:
    """Idempotent sale row for an approved/paid shop order. Returns None if already recorded."""
    existing = (
        await db.execute(select(ShopRevenueLedger).where(ShopRevenueLedger.order_id == order_id).limit(1))
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    method = (payment_method or "card").strip().lower() or "card"
    row = ShopRevenueLedger(
        admin_id=admin_id,
        order_id=order_id,
        entry_type="sale",
        amount_toman=max(0, int(amount_toman or 0)),
        payment_method=method,
        payment_ref=(payment_ref[:128] if payment_ref else None),
        buyer_telegram_id=buyer_telegram_id,
        username=(username[:128] if username else None),
        detail=(detail[:500] if detail else None),
    )
    if getattr(row, "created_at", None) is None:
        row.created_at = datetime.now(UTC)

    bind = await db.connection()
    if bind.dialect.name == "sqlite":
        next_id = (await db.execute(select(func.coalesce(func.max(ShopRevenueLedger.id), 0) + 1))).scalar_one()
        row.id = int(next_id)

    db.add(row)
    if commit:
        await db.commit()
        await db.refresh(row)
    else:
        await db.flush()
    return row


async def list_shop_revenue(
    db: AsyncSession,
    *,
    admin_id: int | None = None,
    payment_method: str | None = None,
    settled: bool | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[ShopRevenueLedger], int]:
    filters = []
    if admin_id is not None:
        filters.append(ShopRevenueLedger.admin_id == admin_id)
    if payment_method:
        filters.append(ShopRevenueLedger.payment_method == payment_method.strip().lower())
    if settled is not None:
        filters.append(ShopRevenueLedger.settled_with_owner.is_(settled))

    base = select(ShopRevenueLedger).where(*filters) if filters else select(ShopRevenueLedger)
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one() or 0)
    stmt = base.order_by(ShopRevenueLedger.id.desc()).offset(offset).limit(limit)
    return list((await db.execute(stmt)).scalars().all()), total


async def shop_revenue_totals_by_gateway(
    db: AsyncSession,
    *,
    admin_id: int | None = None,
) -> list[tuple[str, int, int]]:
    """Return (payment_method, order_count, sum_amount_toman)."""
    filters = [ShopRevenueLedger.entry_type == "sale"]
    if admin_id is not None:
        filters.append(ShopRevenueLedger.admin_id == admin_id)
    stmt = (
        select(
            ShopRevenueLedger.payment_method,
            func.count(ShopRevenueLedger.id),
            func.coalesce(func.sum(ShopRevenueLedger.amount_toman), 0),
        )
        .where(*filters)
        .group_by(ShopRevenueLedger.payment_method)
        .order_by(func.coalesce(func.sum(ShopRevenueLedger.amount_toman), 0).desc())
    )
    rows = (await db.execute(stmt)).all()
    return [(str(r[0] or "card"), int(r[1] or 0), int(r[2] or 0)) for r in rows]


async def set_shop_revenue_settled(
    db: AsyncSession,
    entry_id: int,
    *,
    settled: bool,
    settled_by_admin_id: int | None = None,
) -> ShopRevenueLedger | None:
    row = await db.get(ShopRevenueLedger, entry_id)
    if row is None:
        return None
    row.settled_with_owner = bool(settled)
    row.settled_at = datetime.now(UTC) if settled else None
    row.settled_by_admin_id = settled_by_admin_id if settled else None
    await db.commit()
    await db.refresh(row)
    return row
