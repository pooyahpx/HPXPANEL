"""Meter shared-UUID mother traffic onto local user quotas.

When a mother share link keeps a foreign UUID (Bind UUID off), Xray on a panel
Node still reports that client's traffic — but under a non-integer email, so
``record_usages`` used to drop it. We capture that orphaned traffic and split it
across eligible local users so volume is consumed.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime as dt, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Admin, Node, User, UserStatus
from app.models.settings import ExternalConfig, Subscription
from app.services.mother_config_usage import mother_link_host

logger = logging.getLogger(__name__)

# Prefer users seen online recently when splitting shared mother traffic
_RECENT_ONLINE_WINDOW = timedelta(minutes=5)


def _normalize_host(value: str | None) -> str:
    return (value or "").strip().lower().rstrip(".")


def _cfg_fields(item) -> tuple[bool, bool, bool, str | None]:
    """enabled, personalize (Bind UUID), respect_user_quota, link."""
    if isinstance(item, ExternalConfig):
        return (
            bool(item.enabled),
            bool(item.personalize),
            bool(item.respect_user_quota),
            item.link,
        )
    if isinstance(item, dict):
        return (
            bool(item.get("enabled", True)),
            bool(item.get("personalize", False)),
            bool(item.get("respect_user_quota", True)),
            item.get("link"),
        )
    return (
        bool(getattr(item, "enabled", True)),
        bool(getattr(item, "personalize", False)),
        bool(getattr(item, "respect_user_quota", True)),
        getattr(item, "link", None),
    )


async def mother_node_ids_for_shared_configs(
    db: AsyncSession,
    subscription: Subscription | None,
) -> set[int]:
    """Node ids matching enabled shared-UUID mothers that respect user quota."""
    configs = list(getattr(subscription, "external_configs", None) or [])
    hosts: set[str] = set()
    for item in configs:
        enabled, personalize, respect_quota, link = _cfg_fields(item)
        # Bind UUID off → shared foreign email; only meter when quota is enforced
        if not enabled or personalize or not respect_quota:
            continue
        host = mother_link_host(str(link) if link else None)
        if host:
            hosts.add(host)
    if not hosts:
        return set()

    rows = (await db.execute(select(Node.id, Node.address))).all()
    matched: set[int] = set()
    for node_id, address in rows:
        if _normalize_host(address) in hosts:
            matched.add(int(node_id))
    return matched


async def eligible_mother_user_ids(db: AsyncSession) -> list[int]:
    """Active/on-hold users with remaining volume; prefer recently online."""
    rows = (
        await db.execute(
            select(User.id, User.status, User.data_limit, User.used_traffic, User.online_at)
        )
    ).all()
    now = dt.now(UTC)
    recent_cutoff = now - _RECENT_ONLINE_WINDOW
    all_eligible: list[int] = []
    recent: list[int] = []
    for user_id, status, data_limit, used_traffic, online_at in rows:
        st = status.value if hasattr(status, "value") else str(status or "")
        if st not in {UserStatus.active.value, UserStatus.on_hold.value, "active", "on_hold"}:
            continue
        limit = int(data_limit) if data_limit is not None else 0
        used = int(used_traffic or 0)
        if limit > 0 and used >= limit:
            continue
        uid = int(user_id)
        all_eligible.append(uid)
        if online_at is not None:
            ts = online_at if online_at.tzinfo else online_at.replace(tzinfo=UTC)
            if ts >= recent_cutoff:
                recent.append(uid)
    # Charge online users first; fall back to everyone with remaining quota
    return recent if recent else all_eligible


async def distribute_bytes_to_users(
    db: AsyncSession,
    *,
    user_ids: list[int],
    total_bytes: int,
) -> int:
    """Split ``total_bytes`` across ``user_ids`` (used_traffic + online_at + admin). Returns applied bytes."""
    total_bytes = int(total_bytes or 0)
    if total_bytes <= 0 or not user_ids:
        return 0

    n = len(user_ids)
    base = total_bytes // n
    rem = total_bytes % n
    now = dt.now(UTC)

    # Load admin_id map
    rows = (await db.execute(select(User.id, User.admin_id).where(User.id.in_(user_ids)))).all()
    admin_by_user = {int(uid): admin_id for uid, admin_id in rows if uid is not None}

    admin_delta: dict[int, int] = {}
    applied = 0
    for i, uid in enumerate(user_ids):
        share = base + (1 if i < rem else 0)
        if share <= 0:
            continue
        await db.execute(
            update(User)
            .where(User.id == uid)
            .values(used_traffic=User.used_traffic + share, online_at=now)
        )
        applied += share
        admin_id = admin_by_user.get(uid)
        if admin_id:
            admin_delta[int(admin_id)] = admin_delta.get(int(admin_id), 0) + share

    for admin_id, value in admin_delta.items():
        await db.execute(
            update(Admin).where(Admin.id == admin_id).values(used_traffic=Admin.used_traffic + value)
        )

    await db.commit()
    return applied


async def apply_orphaned_mother_traffic(
    db: AsyncSession,
    *,
    subscription: Subscription | None,
    orphaned_by_node: dict[int, int],
) -> int:
    """Distribute orphaned (non-local-UID) node traffic to eligible mother users.

    Returns total bytes applied to user quotas.
    """
    if not orphaned_by_node:
        return 0

    mother_nodes = await mother_node_ids_for_shared_configs(db, subscription)
    if not mother_nodes:
        logger.debug("No shared-UUID mother configs matched panel nodes; skip orphan metering")
        return 0

    pool = 0
    for node_id, raw in orphaned_by_node.items():
        if int(node_id) in mother_nodes:
            pool += max(0, int(raw or 0))

    if pool <= 0:
        return 0

    user_ids = await eligible_mother_user_ids(db)
    if not user_ids:
        logger.debug("Orphan mother traffic %s bytes but no eligible users", pool)
        return 0

    applied = await distribute_bytes_to_users(db, user_ids=user_ids, total_bytes=pool)
    if applied:
        logger.info(
            "Metered %s bytes of shared mother traffic across %s eligible users (nodes=%s)",
            applied,
            len(user_ids),
            sorted(mother_nodes),
        )
    return applied
