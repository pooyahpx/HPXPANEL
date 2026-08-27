"""Render HPX Pulse tunnel engine TOML — Direct L3 and reverse/port modes."""

from __future__ import annotations

import secrets
from typing import Any

_REVERSE_MODE_TRANSPORT: dict[str, str] = {
    "reverse_stealth": "stealth",
    "reverse_tcp": "tcp",
    "reverse_tcpmux": "tcpmux",
    "reverse_udp": "udp",
    "reverse_kcp": "kcp",
    "reverse_quic": "quic",
    "reverse_ws": "ws",
    "reverse_wss": "wss",
    "reverse_wssmux": "wssmux",
    "reverse_xdi": "xdi",
}

_MUX_TRANSPORTS = frozenset({"tcpmux", "kcp", "wsmux", "wssmux", "xdi"})


def mint_tunnel_token() -> str:
    return secrets.token_urlsafe(32)


def _ports_block(port_forwards: list[str]) -> str:
    if not port_forwards:
        return ""
    quoted = ", ".join(f'"{p}"' for p in port_forwards)
    return f"\nports = [{quoted}]\n"


def _normalize_reverse_ports(port_forwards: list[str]) -> list[str]:
    """Map Iran listen → abroad localhost target.

    '443'         → '443=127.0.0.1:443'
    '443=8443'    → '443=127.0.0.1:8443'
    '443=10.0.0.5:8443' kept as-is
    """
    out: list[str] = []
    for raw in port_forwards:
        p = (raw or "").strip()
        if not p:
            continue
        if "=" not in p:
            out.append(f"{p}=127.0.0.1:{p}")
            continue
        left, right = p.split("=", 1)
        left, right = left.strip(), right.strip()
        if ":" not in right:
            out.append(f"{left}=127.0.0.1:{right}")
        else:
            out.append(f"{left}={right}")
    return out


def _reverse_ports_block(port_forwards: list[str]) -> str:
    ports = _normalize_reverse_ports(port_forwards)
    if not ports:
        return "ports = []\n"
    lines = ["ports = ["]
    for port in ports:
        lines.append(f'  "{port}",')
    lines.append("]")
    return "\n".join(lines) + "\n"


def _reverse_transport(pulse: Any) -> str:
    mode = pulse.tunnel_mode or "direct_l3"
    if mode in _REVERSE_MODE_TRANSPORT:
        return _REVERSE_MODE_TRANSPORT[mode]
    carrier = pulse.carrier or "tcp"
    if carrier in _REVERSE_MODE_TRANSPORT.values():
        return carrier
    return "tcp"


def _server_tls_block(transport: str, domain: str | None) -> str:
    if transport not in {"wss", "wssmux"} or not domain:
        return ""
    return f'acme_domain = "{domain}"\n'


def _mux_block(transport: str) -> str:
    if transport not in _MUX_TRANSPORTS:
        return ""
    return """mux_con = 8
mux_version = 2
mux_framesize = 32768
mux_recievebuffer = 4194304
mux_streambuffer = 65536
"""


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


def render_iran_server(
    *,
    control_port: int,
    token: str,
    transport: str,
    preset: str,
    port_forwards: list[str] | None = None,
    domain: str | None = None,
) -> str:
    ports = _reverse_ports_block(port_forwards or [])
    tls = _server_tls_block(transport, domain)
    mux = _mux_block(transport)
    return f"""[server]
bind_addr = "0.0.0.0:{control_port}"
transport = "{transport}"
preset = "{preset}"
token = "{token}"
nodelay = true
keepalive_period = 75
heartbeat = 20
log_level = "error"
sniffer = false
accept_udp = false
{tls}{mux}{ports}"""


def render_abroad_client(
    *,
    iran_ip: str,
    control_port: int,
    token: str,
    transport: str,
    preset: str,
) -> str:
    mux = _mux_block(transport)
    return f"""[client]
remote_addr = "{iran_ip}:{control_port}"
transport = "{transport}"
preset = "{preset}"
token = "{token}"
connection_pool = 4
keepalive_period = 75
nodelay = true
retry_interval = 3
dial_timeout = 10
log_level = "error"
sniffer = false
{mux}"""


def render_for_side(
    side: str,
    pulse: Any,
    token: str,
) -> str:
    preset = pulse.preset or "balance"
    port_forwards = pulse.port_forwards or []
    mode = pulse.tunnel_mode or "direct_l3"
    domain = getattr(pulse, "domain", None) or None

    if mode.startswith("reverse_"):
        transport = _reverse_transport(pulse)
        if side == "iran":
            return render_iran_server(
                control_port=pulse.control_port,
                token=token,
                transport=transport,
                preset=preset,
                port_forwards=port_forwards,
                domain=domain,
            )
        return render_abroad_client(
            iran_ip=pulse.iran_public_ip,
            control_port=pulse.control_port,
            token=token,
            transport=transport,
            preset=preset,
        )

    carrier = pulse.carrier or "udp"
    common = {
        "control_port": pulse.control_port,
        "token": token,
        "carrier": carrier,
        "preset": preset,
        "port_forwards": port_forwards,
    }
    if side == "iran":
        return render_iran_l3(abroad_ip=pulse.abroad_public_ip, **common)
    return render_abroad_l3(**common)
