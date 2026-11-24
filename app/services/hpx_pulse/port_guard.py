"""Prevent shared-Iran pulses from colliding on control / forward listen ports."""

from __future__ import annotations

from app.services.hpx_pulse.config_linker import forward_listen_ports


class IranPortConflictError(ValueError):
    """Raised when two pulses on the same Iran IP share control or forward ports."""


def find_iran_port_conflicts(
    *,
    iran_ip: str | None,
    control_port: int | None,
    port_forwards: list[str] | None,
    peers: list,
    exclude_pulse_id: int | None = None,
) -> list[str]:
    """Return human-readable conflict messages (empty = OK)."""
    iran = (iran_ip or "").strip()
    if not iran:
        return []
    my_forwards = forward_listen_ports(port_forwards)
    conflicts: list[str] = []
    for peer in peers:
        if exclude_pulse_id is not None and getattr(peer, "id", None) == exclude_pulse_id:
            continue
        peer_iran = (getattr(peer, "iran_public_ip", None) or "").strip()
        if peer_iran != iran:
            continue
        peer_name = getattr(peer, "name", None) or f"#{getattr(peer, 'id', '?')}"
        peer_control = getattr(peer, "control_port", None)
        if control_port and peer_control and int(control_port) == int(peer_control):
            conflicts.append(
                f"Control port {control_port} already used by Pulse «{peer_name}» on Iran {iran}"
            )
        peer_forwards = forward_listen_ports(getattr(peer, "port_forwards", None))
        overlap = sorted(my_forwards & peer_forwards)
        if overlap:
            conflicts.append(
                f"Forward listen port(s) {overlap} already used by Pulse «{peer_name}» on Iran {iran}"
            )
    return conflicts


def merge_peer_forward_ports(peers: list, *, exclude_pulse_id: int | None = None) -> tuple[set[str], dict[str, set[int]]]:
    """Build peer Iran IP set and merged forward-port map (never overwrite same IP)."""
    peer_iran_ips: set[str] = set()
    peer_forward_ports: dict[str, set[int]] = {}
    for peer in peers:
        if exclude_pulse_id is not None and getattr(peer, "id", None) == exclude_pulse_id:
            continue
        pip = (getattr(peer, "iran_public_ip", None) or "").strip()
        if not pip:
            continue
        peer_iran_ips.add(pip)
        peer_forward_ports.setdefault(pip, set()).update(forward_listen_ports(getattr(peer, "port_forwards", None)))
    return peer_iran_ips, peer_forward_ports
