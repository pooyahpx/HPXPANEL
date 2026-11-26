"""Mother-config consumption / eligibility / online stats for the admin UI."""

from __future__ import annotations

from datetime import UTC, datetime as dt, timedelta

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Node, NodeUserUsage, User, UserStatus
from app.models.settings import ExternalConfig, Subscription
from app.services.copilot.proxy_uri import ProxyUriParseError, parse_proxy_link

_ONLINE_WINDOW = timedelta(minutes=2)


class MotherConfigItemUsage(BaseModel):
    name: str = ""
    enabled: bool = True
    respect_user_quota: bool = True
    personalize: bool = False
    host: str | None = None
    matched_node_ids: list[int] = Field(default_factory=list)
    eligible_users: int = 0
    gated_by_quota: int = 0
    gated_by_status: int = 0
    # Users with recent traffic on mother-matched nodes only (not general panel online)
    online_users: int = 0


class MotherConfigUsageResponse(BaseModel):
    total_users: int = 0
    active_users: int = 0
    on_hold_users: int = 0
    limited_users: int = 0
    expired_users: int = 0
    disabled_users: int = 0
    eligible_for_quota_gated: int = 0
    exhausted_volume: int = 0
    unlimited_users: int = 0
    # Distinct eligible users with traffic on any mother-matched node in the last 2 minutes
    online_users: int = 0
    used_traffic_bytes: int = 0
    data_limit_bytes: int = 0
    remaining_bytes: int = 0
    usage_pct: float = Field(default=0.0, description="0–100 across limited eligible users")
    configs: list[MotherConfigItemUsage] = Field(default_factory=list)
    enabled_configs: int = 0
    total_configs: int = 0
    personalized_configs: int = 0
    matched_node_ids: list[int] = Field(default_factory=list)


def _fmt_status(status: UserStatus | str | None) -> str:
    if status is None:
        return ""
    return status.value if hasattr(status, "value") else str(status)


def mother_link_host(link: str | None) -> str | None:
    """Extract hostname from a mother share link (vless/vmess/trojan/ss)."""
    raw = (link or "").strip()
    if not raw:
        return None
    try:
        parsed = parse_proxy_link(raw)
    except ProxyUriParseError:
        return None
    host = (parsed.address or "").strip().lower().rstrip(".")
    return host or None


def _normalize_host(value: str | None) -> str:
    return (value or "").strip().lower().rstrip(".")


def _item_fields(item) -> tuple[str, bool, bool, bool, str | None, int | None]:
    if isinstance(item, ExternalConfig):
        return (
            item.name or "",
            bool(item.enabled),
            bool(item.respect_user_quota),
            bool(item.personalize),
            item.link,
            getattr(item, "node_id", None),
        )
    if isinstance(item, dict):
        node_id = item.get("node_id")
        return (
            str(item.get("name") or ""),
            bool(item.get("enabled", True)),
            bool(item.get("respect_user_quota", True)),
            bool(item.get("personalize", False)),
            item.get("link"),
            int(node_id) if node_id is not None else None,
        )
    node_id = getattr(item, "node_id", None)
    return (
        str(getattr(item, "name", "") or ""),
        bool(getattr(item, "enabled", True)),
        bool(getattr(item, "respect_user_quota", True)),
        bool(getattr(item, "personalize", False)),
        getattr(item, "link", None),
        int(node_id) if node_id is not None else None,
    )


async def _load_nodes_by_host(db: AsyncSession) -> dict[str, list[int]]:
    """Map normalized node.address → node ids (a host may map to multiple nodes)."""
    rows = (await db.execute(select(Node.id, Node.address))).all()
    mapping: dict[str, list[int]] = {}
    for node_id, address in rows:
        key = _normalize_host(address)
        if not key:
            continue
        mapping.setdefault(key, []).append(int(node_id))
    return mapping


async def _online_users_by_node(
    db: AsyncSession,
    node_ids: set[int],
    *,
    since: dt,
) -> dict[int, set[int]]:
    """node_id → set of user_ids with traffic on that node since ``since``."""
    if not node_ids:
        return {}
    stmt = (
        select(NodeUserUsage.node_id, NodeUserUsage.user_id)
        .where(
            NodeUserUsage.node_id.in_(node_ids),
            NodeUserUsage.created_at >= since,
            NodeUserUsage.used_traffic > 0,
        )
        .distinct()
    )
    by_node: dict[int, set[int]] = {}
    for node_id, user_id in (await db.execute(stmt)).all():
        if node_id is None or user_id is None:
            continue
        by_node.setdefault(int(node_id), set()).add(int(user_id))
    return by_node


def _users_on_nodes(by_node: dict[int, set[int]], node_ids: set[int]) -> set[int]:
    out: set[int] = set()
    for nid in node_ids:
        out |= by_node.get(nid, set())
    return out


async def compute_mother_config_usage(
    db: AsyncSession, subscription: Subscription | None
) -> MotherConfigUsageResponse:
    """Aggregate panel-side consumption for mother / external configs.

    Online counts are scoped to traffic on nodes that match each mother link host
    (or an explicit ``node_id``), never general ``User.online_at``.
    """
    configs = list(getattr(subscription, "external_configs", None) or [])
    rows = (
        await db.execute(select(User.id, User.status, User.data_limit, User.used_traffic))
    ).all()
    now = dt.now(UTC)
    since = now - _ONLINE_WINDOW

    total = len(rows)
    by_status = {"active": 0, "on_hold": 0, "limited": 0, "expired": 0, "disabled": 0}
    eligible_ids: set[int] = set()
    status_only_ids: set[int] = set()
    exhausted = 0
    unlimited = 0
    used_sum = 0
    limit_sum = 0
    remaining_sum = 0
    limited_used = 0
    limited_cap = 0

    for user_id, status, data_limit, used_traffic in rows:
        uid = int(user_id)
        st = _fmt_status(status)
        if st in by_status:
            by_status[st] += 1
        used = int(used_traffic or 0)
        limit = int(data_limit) if data_limit is not None else 0
        used_sum += used
        if limit > 0:
            limit_sum += limit

        is_receivable_status = st in {"active", "on_hold"}
        has_quota = limit <= 0 or used < limit
        if is_receivable_status:
            status_only_ids.add(uid)
        if limit <= 0 and is_receivable_status:
            unlimited += 1
        if is_receivable_status and has_quota:
            eligible_ids.add(uid)
            if limit > 0:
                limited_used += used
                limited_cap += limit
                remaining_sum += max(limit - used, 0)
        elif is_receivable_status and not has_quota:
            exhausted += 1

    usage_pct = round((100.0 * limited_used / limited_cap), 1) if limited_cap > 0 else 0.0
    gated_by_status = total - by_status["active"] - by_status["on_hold"]

    nodes_by_host = await _load_nodes_by_host(db)
    all_matched_node_ids: set[int] = set()
    # Only personalized configs can contribute to mother-online (shared UUID is unattributable)
    personalized_matched_node_ids: set[int] = set()
    config_node_map: list[tuple[tuple, set[int], str | None]] = []

    for item in configs:
        name, enabled, respect, personalize, link, explicit_node_id = _item_fields(item)
        host = mother_link_host(str(link) if link else None)
        matched: set[int] = set()
        if explicit_node_id is not None:
            matched.add(int(explicit_node_id))
        if host and host in nodes_by_host:
            matched.update(nodes_by_host[host])
        all_matched_node_ids |= matched
        if enabled and personalize:
            personalized_matched_node_ids |= matched
        config_node_map.append(((name, enabled, respect, personalize, host), matched, host))

    online_by_node = await _online_users_by_node(db, all_matched_node_ids, since=since)
    all_mother_online_users = _users_on_nodes(online_by_node, personalized_matched_node_ids)

    item_usages: list[MotherConfigItemUsage] = []
    for (name, enabled, respect, personalize, host), matched, _host in config_node_map:
        effective_respect = True if not personalize else respect
        if not enabled:
            item_usages.append(
                MotherConfigItemUsage(
                    name=name,
                    enabled=False,
                    respect_user_quota=effective_respect,
                    personalize=personalize,
                    host=host,
                    matched_node_ids=sorted(matched),
                    eligible_users=0,
                    gated_by_quota=0,
                    gated_by_status=gated_by_status,
                    online_users=0,
                )
            )
            continue

        pool = eligible_ids if effective_respect else status_only_ids
        # Shared freeloader UUID never maps to local node stats → online stays 0
        if not personalize or not matched:
            online_count = 0
        else:
            online_count = len(pool & _users_on_nodes(online_by_node, matched))

        item_usages.append(
            MotherConfigItemUsage(
                name=name,
                enabled=True,
                respect_user_quota=effective_respect,
                personalize=personalize,
                host=host,
                matched_node_ids=sorted(matched),
                eligible_users=len(pool),
                gated_by_quota=exhausted if effective_respect else 0,
                gated_by_status=gated_by_status,
                online_users=online_count,
            )
        )

    # Global mother online = distinct eligible users on personalized mother-matched nodes
    global_online = len(eligible_ids & all_mother_online_users) if personalized_matched_node_ids else 0

    return MotherConfigUsageResponse(
        total_users=total,
        active_users=by_status["active"],
        on_hold_users=by_status["on_hold"],
        limited_users=by_status["limited"],
        expired_users=by_status["expired"],
        disabled_users=by_status["disabled"],
        eligible_for_quota_gated=len(eligible_ids),
        exhausted_volume=exhausted,
        unlimited_users=unlimited,
        online_users=global_online,
        used_traffic_bytes=int(used_sum),
        data_limit_bytes=int(limit_sum),
        remaining_bytes=int(remaining_sum),
        usage_pct=usage_pct,
        configs=item_usages,
        enabled_configs=sum(1 for c in item_usages if c.enabled),
        total_configs=len(item_usages),
        personalized_configs=sum(1 for c in item_usages if c.enabled and c.personalize),
        matched_node_ids=sorted(all_matched_node_ids),
    )
