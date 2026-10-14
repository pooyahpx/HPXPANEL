"""Server status for the Telegram shop: match panel hosts (of a Group) to node status."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

ONLINE = "online"
CONNECTING = "connecting"
OFFLINE = "offline"
UNKNOWN = "unknown"

_ONLINE_STATUSES = {"connected", "limited"}
_RANK = {ONLINE: 3, CONNECTING: 2, OFFLINE: 1}


@dataclass(frozen=True)
class NodeInfo:
    name: str
    address: str
    status: str


def node_status_to_state(status: Any) -> str:
    """connected/limited → online, connecting → connecting, anything else → offline."""
    value = str(getattr(status, "value", status) or "").lower()
    if value in _ONLINE_STATUSES:
        return ONLINE
    if value == "connecting":
        return CONNECTING
    return OFFLINE


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _addresses_match(host_addr: str, node_addr: str) -> bool:
    if not host_addr or not node_addr:
        return False
    return host_addr == node_addr or node_addr in host_addr or host_addr in node_addr


def match_host_state(host_addresses: Iterable[str], nodes: Iterable[NodeInfo]) -> str:
    """
    State of a host from the nodes it matches (address equal/contained, or equal to node name).
    Several matching nodes → best state wins (online > connecting > offline).
    No match → UNKNOWN.
    """
    best: str | None = None
    node_list = list(nodes)
    for raw in host_addresses:
        host_addr = _norm(raw)
        if not host_addr or "{" in host_addr:  # placeholders like {SERVER_IP} can't be matched
            continue
        for node in node_list:
            node_addr = _norm(node.address)
            if _addresses_match(host_addr, node_addr) or (_norm(node.name) and host_addr == _norm(node.name)):
                state = node_status_to_state(node.status)
                if best is None or _RANK[state] > _RANK[best]:
                    best = state
    return best or UNKNOWN


def build_server_status_rows(
    hosts: Iterable[tuple[str, Iterable[str]]],
    nodes: Iterable[NodeInfo],
) -> list[tuple[str, str]]:
    """``[(remark, state)]`` deduped by remark (first occurrence order; best state wins on dupes)."""
    node_list = list(nodes)
    order: list[str] = []
    states: dict[str, str] = {}
    for remark, addresses in hosts:
        label = (remark or "").strip() or "—"
        state = match_host_state(addresses, node_list)
        if label not in states:
            order.append(label)
            states[label] = state
        elif _rank(state) > _rank(states[label]):
            states[label] = state
    return [(label, states[label]) for label in order]


def _rank(state: str) -> int:
    return _RANK.get(state, 0)


async def load_server_status_rows(db, group_id: int) -> list[tuple[str, str]] | None:
    """
    Build status rows for a panel Group. Returns None when the group is missing,
    an empty list when it has no (enabled) hosts.
    """
    from sqlalchemy import select

    from app.db.crud.group import get_group_by_id
    from app.db.models import Node, ProxyHost

    group = await get_group_by_id(db, int(group_id), load_users=False, load_inbounds=True)
    if group is None:
        return None
    tags = [inbound.tag for inbound in group.inbounds]
    if not tags:
        return []
    host_rows = (
        (
            await db.execute(
                select(ProxyHost)
                .where(ProxyHost.inbound_tag.in_(tags), ProxyHost.is_disabled.isnot(True))
                .order_by(ProxyHost.priority.asc(), ProxyHost.id.asc())
            )
        )
        .scalars()
        .all()
    )
    node_rows = (await db.execute(select(Node))).scalars().all()
    nodes = [NodeInfo(name=n.name, address=n.address, status=getattr(n.status, "value", n.status)) for n in node_rows]
    return build_server_status_rows(((h.remark, list(h.address or [])) for h in host_rows), nodes)
