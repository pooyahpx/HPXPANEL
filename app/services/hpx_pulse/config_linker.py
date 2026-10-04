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
        has_iran = bool(iran) and any(iran == a or iran in a for a in addrs)
        has_abroad = bool(abroad) and any(abroad == a or abroad in a for a in addrs)
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


def rewrite_host_addresses_to_iran(addresses: Any, *, abroad_ip: str, iran_ip: str) -> set[str]:
    """Replace abroad public IP with Iran IP in a Host.address set."""
    abroad = (abroad_ip or "").strip()
    iran = (iran_ip or "").strip()
    out: set[str] = set()
    for a in _addr_list(addresses):
        if abroad and (a == abroad or abroad in a):
            out.add(iran if iran else a)
        else:
            out.add(a)
    if iran and not out:
        out.add(iran)
    return out
