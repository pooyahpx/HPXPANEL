"""Server status for the Telegram shop: match hosts to Nodes and HPX Pulse tunnels."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

ONLINE = "online"
CONNECTING = "connecting"
OFFLINE = "offline"
UNKNOWN = "unknown"

_ONLINE_NODE = {"connected", "limited"}
_ONLINE_PULSE = {"running"}
_CONNECTING_PULSE = {"starting", "partial"}
_RANK = {ONLINE: 3, CONNECTING: 2, OFFLINE: 1}


@dataclass(frozen=True)
class EndpointInfo:
    """A reachable endpoint that can mark a host online/offline (node or Pulse IP)."""

    name: str
    address: str
    status: str  # already normalized to online|connecting|offline


# Back-compat alias used by older tests / imports
NodeInfo = EndpointInfo


def node_status_to_state(status: Any) -> str:
    """connected/limited → online, connecting → connecting, anything else → offline."""
    value = str(getattr(status, "value", status) or "").lower()
    if value in _ONLINE_NODE:
        return ONLINE
    if value == "connecting":
        return CONNECTING
    return OFFLINE


def pulse_status_to_state(status: Any) -> str:
    """
    HPX Pulse tunnel health → display state.

    running → online; starting/partial → connecting; anything else → offline.
    """
    value = str(getattr(status, "value", status) or "").lower()
    if value in _ONLINE_PULSE:
        return ONLINE
    if value in _CONNECTING_PULSE:
        return CONNECTING
    return OFFLINE


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _addresses_match(host_addr: str, endpoint_addr: str) -> bool:
    if not host_addr or not endpoint_addr:
        return False
    return host_addr == endpoint_addr or endpoint_addr in host_addr or host_addr in endpoint_addr


def match_host_state(host_addresses: Iterable[str], endpoints: Iterable[EndpointInfo]) -> str:
    """
    State of a host from the endpoints it matches (node address/name or Pulse Iran/Abroad IP).

    Several matching endpoints → best state wins (online > connecting > offline).
    No match → UNKNOWN.
    """
    best: str | None = None
    endpoint_list = list(endpoints)
    for raw in host_addresses:
        host_addr = _norm(raw)
        if not host_addr or "{" in host_addr:  # placeholders like {SERVER_IP} can't be matched
            continue
        for ep in endpoint_list:
            ep_addr = _norm(ep.address)
            if _addresses_match(host_addr, ep_addr) or (_norm(ep.name) and host_addr == _norm(ep.name)):
                state = ep.status if ep.status in _RANK else node_status_to_state(ep.status)
                if best is None or _RANK[state] > _RANK[best]:
                    best = state
    return best or UNKNOWN


def build_server_status_rows(
    hosts: Iterable[tuple[str, Iterable[str]]],
    endpoints: Iterable[EndpointInfo],
) -> list[tuple[str, str]]:
    """``[(remark, state)]`` deduped by remark (first occurrence order; best state wins on dupes)."""
    endpoint_list = list(endpoints)
    order: list[str] = []
    states: dict[str, str] = {}
    for remark, addresses in hosts:
        label = (remark or "").strip() or "—"
        state = match_host_state(addresses, endpoint_list)
        if label not in states:
            order.append(label)
            states[label] = state
        elif _rank(state) > _rank(states[label]):
            states[label] = state
    return [(label, states[label]) for label in order]


def _rank(state: str) -> int:
    return _RANK.get(state, 0)


def endpoints_from_nodes(nodes: Iterable[Any]) -> list[EndpointInfo]:
    out: list[EndpointInfo] = []
    for n in nodes:
        out.append(
            EndpointInfo(
                name=str(getattr(n, "name", "") or ""),
                address=str(getattr(n, "address", "") or ""),
                status=node_status_to_state(getattr(n, "status", None)),
            )
        )
    return out


def endpoints_from_pulses(pulses: Iterable[Any]) -> list[EndpointInfo]:
    """
    Each Pulse contributes its Iran + Abroad public IPs as matchable endpoints.

    Hosts on a reverse tunnel usually point at the Iran IP; matching that Pulse IP
    is what makes tunnel configs show Online instead of Unknown.
    """
    out: list[EndpointInfo] = []
    for pulse in pulses:
        if getattr(pulse, "enabled", True) is False:
            continue
        state = pulse_status_to_state(getattr(pulse, "status", None))
        name = str(getattr(pulse, "name", "") or "pulse")
        for raw in (getattr(pulse, "iran_public_ip", None), getattr(pulse, "abroad_public_ip", None)):
            addr = str(raw or "").strip()
            if not addr:
                continue
            out.append(EndpointInfo(name=name, address=addr, status=state))
    return out


async def load_server_status_rows(db, group_id: int) -> list[tuple[str, str]] | None:
    """
    Build status rows for a panel Group. Returns None when the group is missing,
    an empty list when it has no (enabled) hosts.

    Matching order: panel Nodes by address/name, then HPX Pulse Iran/Abroad IPs by tunnel status.
    """
    from sqlalchemy import select

    from app.db.crud.group import get_group_by_id
    from app.db.models import HpxPulse, Node, ProxyHost

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
    pulse_rows = (await db.execute(select(HpxPulse))).scalars().all()
    endpoints = endpoints_from_nodes(node_rows) + endpoints_from_pulses(pulse_rows)
    return build_server_status_rows(((h.remark, list(h.address or [])) for h in host_rows), endpoints)
