"""Server status for the Telegram shop: match hosts to Nodes and HPX Pulse tunnels."""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

ONLINE = "online"
CONNECTING = "connecting"
OFFLINE = "offline"
UNKNOWN = "unknown"

_ONLINE_NODE = {"connected", "limited"}
_ONLINE_PULSE = {"running"}
_CONNECTING_PULSE = {"starting", "partial"}
_RANK = {ONLINE: 3, CONNECTING: 2, OFFLINE: 1}

_MIN_FUZZY_LEN = 3


@dataclass(frozen=True)
class EndpointInfo:
    """A reachable endpoint that can mark a host online/offline (node or Pulse IP/domain)."""

    name: str
    address: str
    status: str  # already normalized to online|connecting|offline


# Back-compat alias used by older tests / imports
NodeInfo = EndpointInfo


@dataclass(frozen=True)
class PulseInfo:
    """Everything about a Pulse tunnel that can be used to recognise a panel Host."""

    name: str
    status: str  # online|connecting|offline
    iran_ip: str = ""
    abroad_ip: str = ""
    domain: str = ""
    forward_ports: frozenset[int] = field(default_factory=frozenset)


@dataclass(frozen=True)
class ServerStatusView:
    """Host rows plus tunnel-health rows for the buyer message."""

    host_rows: list[tuple[str, str]]
    pulse_rows: list[tuple[str, str]]


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


def normalize_label(value: Any) -> str:
    """
    Fuzzy-compare key: lowercase, keep only letters/digits.

    Drops spaces, dashes, underscores, dots, flag emoji and any other symbols, so
    ``🇮🇷 DE-TUN 🇩🇪`` and ``de_tun`` both become ``detun``.
    """
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return "".join(ch for ch in text if ch.isalnum())


def _addresses_match(host_addr: str, endpoint_addr: str) -> bool:
    if not host_addr or not endpoint_addr:
        return False
    return host_addr == endpoint_addr or endpoint_addr in host_addr or host_addr in endpoint_addr


def _better(best: str | None, state: str) -> str:
    if best is None or _RANK.get(state, 0) > _RANK.get(best, 0):
        return state
    return best


def _clean_host_addresses(host_addresses: Iterable[str]) -> list[str]:
    out: list[str] = []
    for raw in host_addresses:
        addr = _norm(raw)
        if addr and "{" not in addr:  # placeholders like {SERVER_IP} can't be matched
            out.append(addr)
    return out


def _address_state(addresses: list[str], endpoints: list[EndpointInfo]) -> str | None:
    """Direct match: host address vs node/Pulse address (IP or domain) or endpoint name."""
    best: str | None = None
    for host_addr in addresses:
        for ep in endpoints:
            ep_addr = _norm(ep.address)
            if _addresses_match(host_addr, ep_addr) or (_norm(ep.name) and host_addr == _norm(ep.name)):
                state = ep.status if ep.status in _RANK else node_status_to_state(ep.status)
                best = _better(best, state)
    return best


def _address_relates_to_pulse(addresses: list[str], pulse: PulseInfo) -> bool:
    """Host address contains/equals Iran IP, abroad IP, domain, or the Pulse name as a label."""
    name_key = normalize_label(pulse.name)
    for addr in addresses:
        for ep_addr in (_norm(pulse.iran_ip), _norm(pulse.abroad_ip), _norm(pulse.domain)):
            if _addresses_match(addr, ep_addr):
                return True
        if name_key:
            if normalize_label(addr) == name_key:
                return True
            # `de-tun.example.com` → label `de-tun` equals the Pulse name
            if len(name_key) >= _MIN_FUZZY_LEN and any(normalize_label(part) == name_key for part in addr.split(".")):
                return True
    return False


def _fuzzy_name_matches(remark: str, pulse_name: str) -> bool:
    a = normalize_label(remark)
    b = normalize_label(pulse_name)
    if len(a) < _MIN_FUZZY_LEN or len(b) < _MIN_FUZZY_LEN:
        return False
    return a in b or b in a


def _port_state(
    port: int | None,
    addresses: list[str],
    remark: str,
    pulses: list[PulseInfo],
) -> str | None:
    """
    Port link: host.port is a Pulse forward listen port.

    Accepted when only one Pulse owns that port, or when several do and the host
    is otherwise related to one of them (address / domain / name).
    """
    if not port:
        return None
    owners = [p for p in pulses if port in p.forward_ports]
    if not owners:
        return None
    if len(owners) > 1:
        owners = [
            p for p in owners if _address_relates_to_pulse(addresses, p) or _fuzzy_name_matches(remark, p.name)
        ]
    best: str | None = None
    for p in owners:
        best = _better(best, p.status)
    return best


def match_host_state(
    host_addresses: Iterable[str],
    endpoints: Iterable[EndpointInfo],
    *,
    remark: str = "",
    port: int | None = None,
    pulses: Iterable[PulseInfo] = (),
) -> str:
    """
    State of a host from the endpoints it matches. Best state wins (online > connecting > offline).

    Order of evidence:
      1. Address equals/contains a node address, or a Pulse Iran/Abroad IP
      2. Address equals/contains ``pulse.domain`` (carried as a Pulse endpoint)
      3. Fuzzy name: normalized remark vs normalized Pulse name (either contains the other, len ≥ 3)
      4. Port link: host.port is a Pulse forward listen port (unique owner, or related by 1-3)
      5. Pulse name used directly as the host address
    No match → UNKNOWN.
    """
    endpoint_list = list(endpoints)
    pulse_list = list(pulses)
    addresses = _clean_host_addresses(host_addresses)

    best = _address_state(addresses, endpoint_list)

    for pulse in pulse_list:
        if _address_relates_to_pulse(addresses, pulse) or _fuzzy_name_matches(remark, pulse.name):
            best = _better(best, pulse.status)

    if best is None:
        best = _port_state(port, addresses, remark, pulse_list)

    return best or UNKNOWN


def _rank(state: str) -> int:
    return _RANK.get(state, 0)


def _inherit_sibling_status(states: dict[str, str]) -> None:
    """
    Fill remaining Unknown hosts from siblings with a shared stem.

    Example: ``DE-TUN`` matched Online via Iran IP, but ``DE-TUN 2`` uses a domain →
    still Unknown. After normalize both are ``detun`` / ``detun2``; inherit Online.
    """
    known = [(label, state) for label, state in states.items() if state != UNKNOWN]
    if not known:
        return
    for label, state in list(states.items()):
        if state != UNKNOWN:
            continue
        key = normalize_label(label)
        if len(key) < _MIN_FUZZY_LEN:
            continue
        best: str | None = None
        for other, other_state in known:
            other_key = normalize_label(other)
            if len(other_key) < _MIN_FUZZY_LEN:
                continue
            # shared stem: detun ⊂ detun2, or equal after stripping trailing digits
            stem_a = key.rstrip("0123456789")
            stem_b = other_key.rstrip("0123456789")
            related = (
                key in other_key
                or other_key in key
                or (len(stem_a) >= _MIN_FUZZY_LEN and stem_a == stem_b)
            )
            if related:
                best = _better(best, other_state)
        if best is not None:
            states[label] = best


def _fill_unknown_from_healthy_pulses(states: dict[str, str], pulses: list[PulseInfo]) -> None:
    """
    When every Pulse is Online and at least one host already matched Online, treat
    remaining Unknown hosts as Online.

    Buyer UI no longer lists Pulse tunnel names. Hosts like ``FL - STUN`` often use a
    domain/remark that never matches ``andishe`` / ``pulse_…`` — without this fill they
    stay Unknown even though every tunnel is up. Requiring one proven Online host avoids
    inventing status when nothing matched.
    """
    if not pulses or not states:
        return
    if not any(state == ONLINE for state in states.values()):
        return
    if not any(state == UNKNOWN for state in states.values()):
        return
    if any(p.status != ONLINE for p in pulses):
        return
    for label, state in list(states.items()):
        if state == UNKNOWN:
            states[label] = ONLINE


def build_server_status_rows(
    hosts: Iterable[tuple],
    endpoints: Iterable[EndpointInfo],
    pulses: Iterable[PulseInfo] = (),
) -> list[tuple[str, str]]:
    """
    ``[(remark, state)]`` deduped by remark (first occurrence order; best state wins on dupes).

    Each host is ``(remark, addresses)`` or ``(remark, addresses, port)``.
    """
    endpoint_list = list(endpoints)
    pulse_list = list(pulses)
    order: list[str] = []
    states: dict[str, str] = {}
    for host in hosts:
        remark, addresses = host[0], host[1]
        port = host[2] if len(host) > 2 else None
        label = (remark or "").strip() or "—"
        state = match_host_state(addresses, endpoint_list, remark=label, port=port, pulses=pulse_list)
        if label not in states:
            order.append(label)
            states[label] = state
        elif _rank(state) > _rank(states[label]):
            states[label] = state
    _inherit_sibling_status(states)
    _fill_unknown_from_healthy_pulses(states, pulse_list)
    return [(label, states[label]) for label in order]


def build_pulse_rows(pulses: Iterable[PulseInfo]) -> list[tuple[str, str]]:
    """Tunnel-health rows ``[(pulse name, state)]`` so buyers always see tunnel health."""
    return [(p.name, p.status) for p in pulses]


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
    Each Pulse contributes its Iran IP, Abroad IP and domain as matchable endpoints.

    Hosts on a reverse tunnel usually point at the Iran IP — or at a domain that
    resolves to it; matching either makes tunnel configs show Online instead of Unknown.
    """
    out: list[EndpointInfo] = []
    for pulse in pulses:
        if getattr(pulse, "enabled", True) is False:
            continue
        state = pulse_status_to_state(getattr(pulse, "status", None))
        name = str(getattr(pulse, "name", "") or "pulse")
        for raw in (
            getattr(pulse, "iran_public_ip", None),
            getattr(pulse, "abroad_public_ip", None),
            getattr(pulse, "domain", None),
        ):
            addr = str(raw or "").strip()
            if not addr:
                continue
            out.append(EndpointInfo(name=name, address=addr, status=state))
    return out


def pulse_infos_from_pulses(pulses: Iterable[Any]) -> list[PulseInfo]:
    from app.services.hpx_pulse.config_linker import forward_listen_ports

    out: list[PulseInfo] = []
    for pulse in pulses:
        if getattr(pulse, "enabled", True) is False:
            continue
        out.append(
            PulseInfo(
                name=str(getattr(pulse, "name", "") or "pulse"),
                status=pulse_status_to_state(getattr(pulse, "status", None)),
                iran_ip=str(getattr(pulse, "iran_public_ip", "") or "").strip(),
                abroad_ip=str(getattr(pulse, "abroad_public_ip", "") or "").strip(),
                domain=str(getattr(pulse, "domain", "") or "").strip(),
                forward_ports=frozenset(forward_listen_ports(getattr(pulse, "port_forwards", None))),
            )
        )
    return out


async def load_server_status(db, group_id: int) -> ServerStatusView | None:
    """
    Build the status view for a panel Group. Returns None when the group is missing.

    ``host_rows`` is empty when the group has no (enabled) hosts. ``pulse_rows`` lists every
    enabled Pulse tunnel so health is visible even when host matching stays Unknown.
    """
    from sqlalchemy import select

    from app.db.crud.group import get_group_by_id
    from app.db.models import HpxPulse, Node, ProxyHost

    group = await get_group_by_id(db, int(group_id), load_users=False, load_inbounds=True)
    if group is None:
        return None

    pulse_models = (await db.execute(select(HpxPulse))).scalars().all()
    pulses = pulse_infos_from_pulses(pulse_models)
    pulse_rows = build_pulse_rows(pulses)

    tags = [inbound.tag for inbound in group.inbounds]
    if not tags:
        return ServerStatusView(host_rows=[], pulse_rows=pulse_rows)
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
    endpoints = endpoints_from_nodes(node_rows) + endpoints_from_pulses(pulse_models)
    rows = build_server_status_rows(
        ((h.remark, list(h.address or []), h.port) for h in host_rows),
        endpoints,
        pulses,
    )
    return ServerStatusView(host_rows=rows, pulse_rows=pulse_rows)


async def load_server_status_rows(db, group_id: int) -> list[tuple[str, str]] | None:
    """Host rows only (back-compat). None when the group is missing."""
    view = await load_server_status(db, group_id)
    return None if view is None else view.host_rows
