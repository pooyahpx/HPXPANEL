from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Group, Node, ProxyInbound, UserGroupQuota, inbounds_groups_association
from app.models.user import UserGroupQuotaInput


async def get_user_group_quotas(db: AsyncSession, user_id: int) -> list[UserGroupQuota]:
    stmt = (
        select(UserGroupQuota)
        .where(UserGroupQuota.user_id == user_id)
        .options(selectinload(UserGroupQuota.group))
    )
    return list((await db.execute(stmt)).scalars().all())


async def sync_user_group_quotas(
    db: AsyncSession,
    user_id: int,
    allowed_group_ids: set[int],
    quotas: list[UserGroupQuotaInput] | None,
) -> None:
    if quotas is None:
        return

    existing = {q.group_id: q for q in await get_user_group_quotas(db, user_id)}
    incoming = {item.group_id: item for item in quotas if item.group_id in allowed_group_ids and item.data_limit}

    for group_id, row in existing.items():
        if group_id not in incoming:
            await db.delete(row)

    for group_id, item in incoming.items():
        limit = item.data_limit or None
        if group_id in existing:
            existing[group_id].data_limit = limit
        else:
            db.add(UserGroupQuota(user_id=user_id, group_id=group_id, data_limit=limit, used_traffic=0))


async def reset_user_group_quotas(db: AsyncSession, user_id: int) -> None:
    stmt = select(UserGroupQuota).where(UserGroupQuota.user_id == user_id)
    for row in (await db.execute(stmt)).scalars().all():
        row.used_traffic = 0


async def get_group_inbound_tags(db: AsyncSession) -> dict[int, set[str]]:
    stmt = (
        select(Group.id, ProxyInbound.tag)
        .join(inbounds_groups_association, Group.id == inbounds_groups_association.c.group_id)
        .join(ProxyInbound, inbounds_groups_association.c.inbound_id == ProxyInbound.id)
    )
    mapping: dict[int, set[str]] = defaultdict(set)
    for group_id, tag in (await db.execute(stmt)).all():
        mapping[group_id].add(tag)
    return dict(mapping)


async def get_node_inbound_tags(db: AsyncSession, node_ids: list[int]) -> dict[int, set[str]]:
    if not node_ids:
        return {}
    from app.core.manager import core_manager

    stmt = select(Node.id, Node.core_config_id).where(Node.id.in_(node_ids))
    rows = (await db.execute(stmt)).all()
    core_ids = {core_id for _, core_id in rows if core_id is not None}
    cores = await core_manager.get_cores(core_ids | {1}) if core_ids else {}
    mapping: dict[int, set[str]] = {}
    for node_id, core_id in rows:
        core = cores.get(core_id) or cores.get(1)
        mapping[node_id] = set(core.inbounds or []) if core else set()
    return mapping


async def record_group_quota_usage(
    db: AsyncSession,
    *,
    node_params: dict[int, list[dict]],
    usage_coefficient: dict[int, float],
    valid_user_ids: set[int],
) -> set[int]:
    """Attribute node usage to per-group quotas. Returns user ids that newly hit a group limit."""
    if not node_params or not valid_user_ids:
        return set()

    stmt = select(UserGroupQuota).where(
        UserGroupQuota.user_id.in_(valid_user_ids),
        UserGroupQuota.data_limit.isnot(None),
        UserGroupQuota.data_limit > 0,
    )
    quotas = list((await db.execute(stmt)).scalars().all())
    if not quotas:
        return set()

    quotas_by_user: dict[int, list[UserGroupQuota]] = defaultdict(list)
    for quota in quotas:
        quotas_by_user[quota.user_id].append(quota)

    group_tags = await get_group_inbound_tags(db)
    node_tags = await get_node_inbound_tags(db, list(node_params.keys()))

    deltas: dict[tuple[int, int], int] = defaultdict(int)
    for node_id, params in node_params.items():
        tags = node_tags.get(node_id) or set()
        if not tags:
            continue
        coeff = usage_coefficient.get(node_id, 1)
        for param in params:
            uid = int(param["uid"])
            if uid not in valid_user_ids:
                continue
            value = int(param["value"] * coeff)
            if value <= 0:
                continue
            user_quotas = quotas_by_user.get(uid)
            if not user_quotas:
                continue
            matching: list[int] = []
            for quota in user_quotas:
                if (group_tags.get(quota.group_id) or set()) & tags:
                    matching.append(quota.group_id)
            if not matching:
                continue
            share = value // len(matching)
            if share <= 0:
                continue
            for group_id in matching:
                deltas[(uid, group_id)] += share

    if not deltas:
        return set()

    quota_lookup = {(q.user_id, q.group_id): q for q in quotas}
    users_to_sync: set[int] = set()
    for (uid, group_id), delta in deltas.items():
        quota = quota_lookup.get((uid, group_id))
        if quota is None:
            continue
        was_limited = quota.is_limited
        quota.used_traffic += delta
        if not was_limited and quota.is_limited:
            users_to_sync.add(uid)

    await db.commit()
    return users_to_sync
