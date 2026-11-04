"""Render HPX Pulse tunnel engine TOML — Direct L3 and reverse/port modes."""

from __future__ import annotations

import secrets
from typing import Any

# Default MSS for reverse [server]/[client]. Iran↔abroad paths that drop large
# TCP segments (UDP still OK) need a lower clamp — see Safe / MTU advisor profiles.
DEFAULT_MSS = 1280
MTU_SAFE_MSS = 1200
MTU_HARD_MSS = 1100
MTU_EXTREME_MSS = 1000

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

# Panel profile_id → TCP MSS / L3 mss_clamp. Engine preset stays balance/turbo/…
# (do not invent engine preset names). Only emit keys the binary already understands.
_MSS_BY_PROFILE: dict[str, int] = {
    "pulse-reverse-tcp-stealth-mtu": MTU_SAFE_MSS,
    "pulse-reverse-tcp-mtu": MTU_SAFE_MSS,
    "pulse-reverse-tcp-stealth-mtu-hard": MTU_HARD_MSS,
    "pulse-reverse-tcp-stealth-mtu-extreme": MTU_EXTREME_MSS,
    "pulse-reverse-tcp-mtu-extreme": MTU_EXTREME_MSS,
}


def mint_tunnel_token() -> str:
    return secrets.token_urlsafe(32)


def resolve_mss(pulse: Any) -> int:
    """TCP MSS (reverse) / mss_clamp (L3) for this pulse — profile-driven."""
    explicit = getattr(pulse, "mss", None)
    if isinstance(explicit, int) and explicit > 0:
        return explicit
    profile_id = getattr(pulse, "profile_id", None) or ""
    if profile_id in _MSS_BY_PROFILE:
        return _MSS_BY_PROFILE[profile_id]
    return DEFAULT_MSS


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
    # Large frames (32KiB) stall on Iran paths even over KCP/QUIC when path MTU is low.
    # Keep bigger frames for TCP-family mux; clamp UDP carriers.
    if transport in {"kcp", "quic", "xdi"}:
        return """mux_con = 8
mux_version = 2
mux_framesize = 4096
mux_recievebuffer = 4194304
mux_streambuffer = 32768
"""
    return """mux_con = 8
mux_version = 2
mux_framesize = 32768
mux_recievebuffer = 4194304
mux_streambuffer = 65536
"""


_VALID_SPOOF_PROFILES = frozenset(
    {"udp", "icmp", "tcp", "icmpv6", "proto58", "ipip", "gre"}
)


def _spoof_config_dict(pulse: Any) -> dict:
    raw = getattr(pulse, "spoof_config", None)
    return raw if isinstance(raw, dict) else {}


def _spoof_toml_block(
    *,
    side: str,
    pulse: Any,
    carrier: str,
) -> str:
    """Emit spoof_* keys for [l3] when carrier=spoof. Empty string otherwise."""
    if (carrier or "").lower() != "spoof":
        return ""
    cfg = _spoof_config_dict(pulse)
    profile = str(cfg.get("profile") or "udp").strip().lower()
    if profile not in _VALID_SPOOF_PROFILES:
        profile = "udp"
    stealth = bool(cfg.get("stealth"))
    lines = [f'spoof_profile = "{profile}"']

    # Iran (dial) must know Abroad's REAL public IPv4 — forged replies cannot be learned from the wire.
    if side == "iran":
        peer_real = (getattr(pulse, "abroad_public_ip", None) or "").strip()
        if peer_real:
            lines.append(f'spoof_peer_ip = "{peer_real}"')
    else:
        # Optional on abroad; default comes from dial addr host. Still emit Iran real IP when known.
        iran_real = (getattr(pulse, "iran_public_ip", None) or "").strip()
        if iran_real:
            lines.append(f'spoof_peer_ip = "{iran_real}"')

    # Per-side forged source overrides a shared src_ip.
    side_key = "iran_src_ip" if side == "iran" else "abroad_src_ip"
    src = str(cfg.get(side_key) or cfg.get("src_ip") or "").strip()
    if src:
        lines.append(f'spoof_src_ip = "{src}"')

    pool = cfg.get("src_pool") or []
    if isinstance(pool, str):
        pool = [p.strip() for p in pool.split(",") if p.strip()]
    if isinstance(pool, list) and pool:
        quoted = ", ".join(f'"{str(p).strip()}"' for p in pool if str(p).strip())
        if quoted:
            lines.append(f"spoof_src_pool = [{quoted}]")

    mtu = cfg.get("mtu")
    if isinstance(mtu, int) and mtu > 0:
        lines.append(f"spoof_mtu = {mtu}")
    sockbuf = cfg.get("sockbuf")
    if isinstance(sockbuf, int) and sockbuf > 0:
        lines.append(f"spoof_sockbuf = {sockbuf}")

    if cfg.get("icmp_reply"):
        lines.append("spoof_icmp_reply = true")

    # Stealth is one switch in the panel — expands to the wire-changing + local fingerprint group.
    if stealth:
        lines.append("spoof_padding = true")
        lines.append("spoof_padding_max = 32")
        lines.append("spoof_ttl_jitter = true")
        lines.append("spoof_random_dscp = true")
        lines.append("spoof_shuffle_port = true")
        if profile == "tcp":
            lines.append("spoof_fake_tls = true")

    return "\n".join(lines) + "\n"


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
    mss_clamp: int = DEFAULT_MSS,
    spoof_block: str = "",
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
mss_clamp = {mss_clamp}
iface = "bp0"
{spoof_block}{ports}"""


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
    mss_clamp: int = DEFAULT_MSS,
    spoof_block: str = "",
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
mss_clamp = {mss_clamp}
iface = "bp0"
{spoof_block}{ports}"""


def render_iran_server(
    *,
    control_port: int,
    token: str,
    transport: str,
    preset: str,
    port_forwards: list[str] | None = None,
    domain: str | None = None,
    mss: int = DEFAULT_MSS,
) -> str:
    ports = _reverse_ports_block(port_forwards or [])
    tls = _server_tls_block(transport, domain)
    mux = _mux_block(transport)
    # Iran↔abroad paths often drop large TCP segments (UDP still works). Clamp MSS
    # like BackPack Health Check recommends when path MTU < 1500.
    mss_line = f"mss = {mss}\n" if mss and mss > 0 else ""
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
accept_udp = true
{mss_line}{tls}{mux}{ports}"""


def render_abroad_client(
    *,
    iran_ip: str,
    control_port: int,
    token: str,
    transport: str,
    preset: str,
    mss: int = DEFAULT_MSS,
) -> str:
    mux = _mux_block(transport)
    mss_line = f"mss = {mss}\n" if mss and mss > 0 else ""
    return f"""[client]
remote_addr = "{iran_ip}:{control_port}"
transport = "{transport}"
preset = "{preset}"
token = "{token}"
connection_pool = 8
keepalive_period = 75
nodelay = true
retry_interval = 3
dial_timeout = 10
log_level = "error"
sniffer = false
{mss_line}{mux}"""


def render_for_side(
    side: str,
    pulse: Any,
    token: str,
) -> str:
    preset = pulse.preset or "balance"
    port_forwards = pulse.port_forwards or []
    mode = pulse.tunnel_mode or "direct_l3"
    domain = getattr(pulse, "domain", None) or None
    mss = resolve_mss(pulse)

    carrier = pulse.carrier or "udp"
    if (carrier or "").lower() == "spoof" and mode.startswith("reverse_"):
        raise ValueError("carrier=spoof is Direct L3 only — refuse reverse rendering")

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
                mss=mss,
            )
        return render_abroad_client(
            iran_ip=pulse.iran_public_ip,
            control_port=pulse.control_port,
            token=token,
            transport=transport,
            preset=preset,
            mss=mss,
        )

    spoof_block = _spoof_toml_block(side=side, pulse=pulse, carrier=carrier)
    common = {
        "control_port": pulse.control_port,
        "token": token,
        "carrier": carrier,
        "preset": preset,
        "port_forwards": port_forwards,
        "mss_clamp": mss,
        "spoof_block": spoof_block,
    }
    if side == "iran":
        return render_iran_l3(abroad_ip=pulse.abroad_public_ip, **common)
    return render_abroad_l3(**common)
