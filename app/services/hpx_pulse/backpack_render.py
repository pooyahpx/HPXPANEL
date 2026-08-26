"""Render BackPack L3 TOML for Iran (dial) and abroad (listen) sides."""

from __future__ import annotations

import secrets
from typing import Any


def mint_backpack_token() -> str:
    return secrets.token_urlsafe(32)


def _ports_block(port_forwards: list[str]) -> str:
    if not port_forwards:
        return ""
    quoted = ", ".join(f'"{p}"' for p in port_forwards)
    return f"\nports = [{quoted}]\n"


def render_iran_l3(
    *,
    abroad_ip: str,
    control_port: int,
    token: str,
    carrier: str,
    preset: str,
    local_ip: str = "10.10.0.1/30",
    peer_ip: str = "10.10.0.2",
    port_forwards: list[str] | None = None,
    mtu: int = 1380,
) -> str:
    ports = _ports_block(port_forwards or [])
    return f"""[l3]
mode = "dial"
addr = "{abroad_ip}:{control_port}"
token = "{token}"
local_ip = "{local_ip}"
peer_ip = "{peer_ip}"
carrier = "{carrier}"
preset = "{preset}"
mtu = {mtu}
auto_mtu = true
mss_clamp = 0
iface = "bp0"
{ports}"""


def render_abroad_l3(
    *,
    control_port: int,
    token: str,
    carrier: str,
    preset: str,
    local_ip: str = "10.10.0.2/30",
    peer_ip: str = "10.10.0.1",
    port_forwards: list[str] | None = None,
    mtu: int = 1380,
) -> str:
    ports = _ports_block(port_forwards or [])
    return f"""[l3]
mode = "listen"
addr = "0.0.0.0:{control_port}"
token = "{token}"
local_ip = "{local_ip}"
peer_ip = "{peer_ip}"
carrier = "{carrier}"
preset = "{preset}"
mtu = {mtu}
auto_mtu = true
mss_clamp = 0
iface = "bp0"
{ports}"""


def render_for_side(
    side: str,
    pulse: Any,
    token: str,
) -> str:
    carrier = pulse.carrier or "udp"
    if pulse.tunnel_mode == "reverse_kcp":
        carrier = "udp"
    common = {
        "control_port": pulse.control_port,
        "token": token,
        "carrier": carrier,
        "preset": pulse.preset or "balance",
        "port_forwards": pulse.port_forwards or [],
    }
    if side == "iran":
        return render_iran_l3(abroad_ip=pulse.abroad_public_ip, **common)
    return render_abroad_l3(**common)
