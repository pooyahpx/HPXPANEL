"""Host traffic coefficients — global (on host) and per-user overrides."""

from __future__ import annotations

from sqlalchemy import delete, insert, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Group,
    ProxyHost,
    ProxyInbound,
    User,
    UserHostCoefficient,
    inbounds_groups_association,
    users_groups_association,
)


async def get_host_by_id(db: AsyncSession, host_id: int) -> ProxyHost | None:
    return await db.get(ProxyHost, host_id)


async def list_user_host_coefficients(db: AsyncSession, host_id: int) -> list[UserHostCoefficient]:
    stmt = select(UserHostCoefficient).where(UserHostCoefficient.host_id == host_id)
    return list((await db.execute(stmt)).scalars().all())


async def list_user_host_coefficients_with_usernames(
    db: AsyncSession, host_id: int
) -> list[tuple[UserHostCoefficient, str]]:
    stmt = (
        select(UserHostCoefficient, User.username)
        .join(User, User.id == UserHostCoefficient.user_id)
        .where(UserHostCoefficient.host_id == host_id)
        .order_by(User.username)
    )
    return list((await db.execute(stmt)).all())


async def upsert_user_host_coefficient(
    db: AsyncSession, *, user_id: int, host_id: int, usage_coefficient: float, commit: bool = True
) -> UserHostCoefficient:
    dialect = db.bind.dialect.name
    coeff = float(usage_coefficient)
    values = {"user_id": user_id, "host_id": host_id, "usage_coefficient": coeff}
    if dialect == "postgresql":
        stmt = pg_insert(UserHostCoefficient).values(**values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_user_host_coefficients_user_host",
            set_={"usage_coefficient": coeff},
        )
    elif dialect == "mysql":
        stmt = mysql_insert(UserHostCoefficient).values(**values)
        stmt = stmt.on_duplicate_key_update(usage_coefficient=coeff)
    else:
        existing = (
            await db.execute(
                select(UserHostCoefficient).where(
                    UserHostCoefficient.user_id == user_id,
                    UserHostCoefficient.host_id == host_id,
                )
            )
        ).scalar_one_or_none()
        if existing:
            existing.usage_coefficient = coeff
            if commit:
                await db.commit()
                await db.refresh(existing)
            return existing
        stmt = insert(UserHostCoefficient).values(**values)
    await db.execute(stmt)
    if commit:
        await db.commit()
    row = (
        await db.execute(
            select(UserHostCoefficient).where(
                UserHostCoefficient.user_id == user_id,
                UserHostCoefficient.host_id == host_id,
            )
        )
    ).scalar_one()
    return row


async def delete_user_host_coefficient(db: AsyncSession, *, user_id: int, host_id: int) -> bool:
    result = await db.execute(
        delete(UserHostCoefficient).where(
            UserHostCoefficient.user_id == user_id,
            UserHostCoefficient.host_id == host_id,
        )
    )
    await db.commit()
    return bool(result.rowcount)


async def user_ids_with_access_to_host(db: AsyncSession, host: ProxyHost) -> list[int]:
    """Users whose groups include this host's inbound."""
    if not host.inbound_tag:
        return []
    stmt = (
        select(User.id)
        .join(users_groups_association, User.id == users_groups_association.c.user_id)
        .join(Group, Group.id == users_groups_association.c.groups_id)
        .join(inbounds_groups_association, Group.id == inbounds_groups_association.c.group_id)
        .join(ProxyInbound, ProxyInbound.id == inbounds_groups_association.c.inbound_id)
        .where(ProxyInbound.tag == host.inbound_tag)
        .distinct()
    )
    return [int(uid) for uid in (await db.execute(stmt)).scalars().all()]


async def apply_host_coefficient_to_all_users(
    db: AsyncSession, *, host: ProxyHost, usage_coefficient: float | None = None
) -> int:
    """Upsert per-user overrides for every user who can access this host."""
    coeff = float(usage_coefficient if usage_coefficient is not None else (host.usage_coefficient or 1.0))
    if coeff <= 0:
        coeff = 1.0
    user_ids = await user_ids_with_access_to_host(db, host)
    for uid in user_ids:
        await upsert_user_host_coefficient(db, user_id=uid, host_id=host.id, usage_coefficient=coeff, commit=False)
    await db.commit()
    return len(user_ids)


async def load_effective_host_coefficients_for_users(db: AsyncSession, uids: set[int]) -> dict[int, float]:
    """Max host traffic factor per user (override wins over host default)."""
    if not uids:
        return {}
    stmt = (
        select(
            User.id,
            ProxyHost.id,
            ProxyHost.usage_coefficient,
            UserHostCoefficient.usage_coefficient,
        )
        .join(users_groups_association, User.id == users_groups_association.c.user_id)
        .join(Group, Group.id == users_groups_association.c.groups_id)
        .join(inbounds_groups_association, Group.id == inbounds_groups_association.c.group_id)
        .join(ProxyInbound, ProxyInbound.id == inbounds_groups_association.c.inbound_id)
        .join(ProxyHost, ProxyHost.inbound_tag == ProxyInbound.tag)
        .outerjoin(
            UserHostCoefficient,
            (UserHostCoefficient.user_id == User.id) & (UserHostCoefficient.host_id == ProxyHost.id),
        )
        .where(User.id.in_(list(uids)))
    )
    factors: dict[int, float] = {int(uid): 1.0 for uid in uids}
    for uid, _host_id, host_coeff, override in (await db.execute(stmt)).all():
        try:
            base = float(host_coeff) if host_coeff is not None else 1.0
        except (TypeError, ValueError):
            base = 1.0
        try:
            ov = float(override) if override is not None else None
        except (TypeError, ValueError):
            ov = None
        value = ov if ov is not None and ov > 0 else (base if base > 0 else 1.0)
        uid_i = int(uid)
        if value > factors.get(uid_i, 1.0):
            factors[uid_i] = value
    return factors
