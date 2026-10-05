"""Find panel Hosts that should ride a Pulse reverse tunnel (Iran address)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LinkedHostHit:
    host_id: int
    remark: str
    port: int | None
    addresses: list[str]
    issue: str  # abroad_ip | mixed | ok_iran | other
    detail: str


def _addr_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, (set, list, tuple)):
        return [str(a).strip() for a in raw if str(a).strip()]
    s = str(raw).strip()
    return [s] if s else []


def forward_listen_ports(port_forwards: list[str] | None) -> set[int]:
    """External listen ports from pulse forwards (left side of 8443=127.0.0.1:8443)."""
    out: set[int] = set()
    for raw in port_forwards or []:
        left = str(raw).split("=", 1)[0].strip()
        left = left.split(":", 1)[0].strip()
        if left.isdigit():
            port = int(left)
            if 1 <= port <= 65535:
                out.add(port)
    return out


def scan_hosts_for_pulse(
    hosts: list[Any],
    *,
    iran_ip: str | None,
    abroad_ip: str | None,
) -> list[LinkedHostHit]:
    """Classify subscription Hosts relative to this Pulse's public IPs."""
    iran = (iran_ip or "").strip()
    abroad = (abroad_ip or "").strip()
    hits: list[LinkedHostHit] = []
    if not iran and not abroad:
        return hits

    for h in hosts:
        addrs = _addr_list(getattr(h, "address", None))
        if not addrs:
            continue
        has_iran = bool(iran) and any(iran == a for a in addrs)
        has_abroad = bool(abroad) and any(abroad == a for a in addrs)
        if not has_iran and not has_abroad:
            continue
        if has_abroad and not has_iran:
            issue = "abroad_ip"
            detail = (
                f"Host «{getattr(h, 'remark', '?')}» points at abroad IP {abroad} — "
                "clients bypass the Iran tunnel (ping works without Pulse). "
                f"Set address to Iran IP {iran} so traffic enters the reverse TCP forward."
            )
        elif has_abroad and has_iran:
            issue = "mixed"
            detail = (
                f"Host «{getattr(h, 'remark', '?')}» mixes Iran and abroad addresses — "
                "remove abroad IP; keep only Iran."
            )
        else:
            issue = "ok_iran"
            detail = f"Host «{getattr(h, 'remark', '?')}» uses Iran IP (tunnel path)."
        hits.append(
            LinkedHostHit(
                host_id=int(getattr(h, "id", 0) or 0),
                remark=str(getattr(h, "remark", "") or ""),
                port=getattr(h, "port", None),
                addresses=addrs,
                issue=issue,
                detail=detail,
            )
        )
    return hits


def host_belongs_to_other_pulse(
    *,
    addresses: list[str],
    host_port: int | None,
    my_iran_ip: str,
    my_forward_ports: set[int],
    peer_iran_ips: set[str],
    peer_forward_ports: dict[str, set[int]],
) -> bool:
    """True when this Host is already wired to a different Pulse (don't steal it)."""
    my_iran = (my_iran_ip or "").strip()
    for addr in addresses:
        a = addr.strip()
        if not a or a == my_iran:
            continue
        if a in peer_iran_ips:
            peer_ports = peer_forward_ports.get(a) or set()
            # Same Iran IP on two pulses: use port to decide ownership.
            if host_port and peer_ports and host_port in peer_ports:
                return True
            if host_port and my_forward_ports and host_port in my_forward_ports:
                return False
            # Different Iran IP entirely → owned by the other pulse.
            if a != my_iran:
                return True
    if host_port and my_forward_ports and host_port not in my_forward_ports:
        # Port matches another pulse's forwards only.
        for ports in peer_forward_ports.values():
            if host_port in ports:
                return True
    return False


def rewrite_host_addresses_to_iran(
    addresses: Any,
    *,
    abroad_ip: str,
    iran_ip: str,
    protected_iran_ips: set[str] | None = None,
) -> set[str]:
    """Replace abroad public IP with Iran IP in a Host.address set.

    Never rewrite addresses that already point at another Pulse's Iran IP
    (shared abroad VPS + Diagnose must not steal sibling tunnels' Hosts).
    """
    abroad = (abroad_ip or "").strip()
    iran = (iran_ip or "").strip()
    protected = {p.strip() for p in (protected_iran_ips or set()) if p and p.strip() and p.strip() != iran}
    out: set[str] = set()
    for a in _addr_list(addresses):
        if a in protected:
            out.add(a)
            continue
        if abroad and a == abroad:
            out.add(iran if iran else a)
        else:
            out.add(a)
    if iran and not out:
        out.add(iran)
    return out
