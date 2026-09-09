"""CRUD for create-budget accounting ledger."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Admin, CreateBudgetLedger


async def add_create_budget_ledger_entry(
    db: AsyncSession,
    *,
    admin_id: int,
    entry_type: str,
    amount_toman: int,
    balance_after: int,
    actor_admin_id: int | None = None,
    user_id: int | None = None,
    username: str | None = None,
    billable_gb: int = 0,
    billable_days: int = 0,
    price_per_gb: int | None = None,
    price_per_day: int | None = None,
    pricing_mode: str | None = None,
    tier_gb: int | None = None,
    detail: str | None = None,
    commit: bool = True,
) -> CreateBudgetLedger:
    from sqlalchemy import func

    row = CreateBudgetLedger(
        admin_id=admin_id,
        entry_type=entry_type,
        amount_toman=int(amount_toman),
        balance_after=int(balance_after),
        actor_admin_id=actor_admin_id,
        user_id=user_id,
        username=username,
        billable_gb=int(billable_gb or 0),
        billable_days=int(billable_days or 0),
        price_per_gb=price_per_gb,
        price_per_day=price_per_day,
        pricing_mode=pricing_mode,
        tier_gb=tier_gb,
        detail=(detail[:500] if detail else None),
    )
    if getattr(row, "created_at", None) is None:
        row.created_at = datetime.now(UTC)

    bind = await db.connection()
    if bind.dialect.name == "sqlite":
        next_id = (await db.execute(select(func.coalesce(func.max(CreateBudgetLedger.id), 0) + 1))).scalar_one()
        row.id = int(next_id)

    db.add(row)
    if commit:
        await db.commit()
        await db.refresh(row)
    else:
        await db.flush()
    return row


async def list_create_budget_ledger(
    db: AsyncSession,
    *,
    admin_id: int | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[CreateBudgetLedger], int]:
    from sqlalchemy import func

    filters = []
    if admin_id is not None:
        filters.append(CreateBudgetLedger.admin_id == admin_id)

    count_stmt = select(func.count(CreateBudgetLedger.id))
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = int((await db.execute(count_stmt)).scalar_one() or 0)

    stmt = select(CreateBudgetLedger).order_by(CreateBudgetLedger.id.desc())
    if filters:
        stmt = stmt.where(*filters)
    stmt = stmt.offset(max(0, offset)).limit(max(1, min(limit, 200)))
    rows = list((await db.execute(stmt)).scalars().all())
    return rows, total


async def get_admin_usernames_map(db: AsyncSession, admin_ids: set[int]) -> dict[int, str]:
    if not admin_ids:
        return {}
    rows = (await db.execute(select(Admin.id, Admin.username).where(Admin.id.in_(admin_ids)))).all()
    return {int(admin_id): username for admin_id, username in rows}
