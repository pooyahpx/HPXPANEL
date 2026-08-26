"""Rule-based auto-heal for HPX ICMP tunnels (no LLM)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime as dt, timedelta as td
from enum import Enum

from app.db.models import HpxTunnel, HpxTunnelRole, HpxTunnelStatus
from app.db.crud.hpx_tunnel import is_agent_managed
from app.services.hpx_tunnel.manager import (
    _assign_interface_ip,
    apply_icmp_kernel_hardening,
    get_container_logs,
    inspect_runtime,
    start_tunnel,
    stop_containers_using_interface,
)
from app.utils.logger import get_logger

logger = get_logger("hpx-tunnel-healer")

HEAL_COOLDOWN = td(minutes=5)
HEAL_MAX_PER_HOUR = 3
AGENT_STALE_SECONDS = 90
STUCK_STARTING_SECONDS = 120
MIN_KEEPALIVE = 30


class HealAction(str, Enum):
    none = "none"
    restart_foreign = "restart_foreign"
    reassign_iface = "reassign_iface"
    stop_conflicts = "stop_conflicts"
    sysctl_icmp_ignore = "sysctl_icmp_ignore"
    bump_keepalive_restart = "bump_keepalive_restart"
    agent_restart = "agent_restart"
    agent_start = "agent_start"
    unstuck_starting = "unstuck_starting"


@dataclass
class HealIssue:
    code: str
    message: str
    suggested_action: HealAction


@dataclass
class HealResult:
    issues: list[HealIssue] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)
    repaired: bool = False
    skipped_reason: str | None = None


_KEEPALIVE_RE = re.compile(r"Keepalive timeout", re.I)
_BUSY_RE = re.compile(r"device or resource busy", re.I)
_RTNETLINK_RE = re.compile(r"Operation not permitted", re.I)


def _reset_heal_window_if_stale(tunnel: HpxTunnel) -> None:
    if tunnel.last_heal_at and dt.now(UTC) - tunnel.last_heal_at >= td(hours=1):
        tunnel.heal_count_window = 0


def _heal_allowed(tunnel: HpxTunnel, action: HealAction) -> tuple[bool, str | None]:
    _ = action
    if not tunnel.auto_heal_enabled:
        return False, "auto-heal disabled"
    _reset_heal_window_if_stale(tunnel)
    now = dt.now(UTC)
    if tunnel.last_heal_at and now - tunnel.last_heal_at < HEAL_COOLDOWN:
        return False, "cooldown active"
    if (tunnel.heal_count_window or 0) >= HEAL_MAX_PER_HOUR:
        return False, "hourly heal limit reached"
    return True, None


def diagnose_tunnel(tunnel: HpxTunnel, runtime, logs: str = "") -> list[HealIssue]:
    issues: list[HealIssue] = []
    logs_lower = (logs or tunnel.message or "").lower()

    if tunnel.status == HpxTunnelStatus.starting and tunnel.last_status_change:
        age = (dt.now(UTC) - tunnel.last_status_change).total_seconds()
        if age > STUCK_STARTING_SECONDS:
            issues.append(
                HealIssue(
                    "stuck_starting",
                    f"Tunnel stuck in starting for {int(age)}s",
                    HealAction.unstuck_starting,
                )
            )

    if tunnel.role == HpxTunnelRole.foreign and not is_agent_managed(tunnel):
        if not runtime.container_running:
            issues.append(
                HealIssue(
                    "container_down",
                    "FOREIGN container is not running",
                    HealAction.restart_foreign,
                )
            )
        elif not runtime.interface_up:
            issues.append(
                HealIssue(
                    "iface_down",
                    f"Interface {tunnel.interface} has no IP or is down",
                    HealAction.reassign_iface,
                )
            )

    if _BUSY_RE.search(logs_lower):
        issues.append(
            HealIssue(
                "iface_busy",
                "TAP interface busy (duplicate tunnel containers?)",
                HealAction.stop_conflicts,
            )
        )

    if _KEEPALIVE_RE.search(logs_lower) or (
        tunnel.packet_loss_pct is not None and tunnel.packet_loss_pct >= 100
    ):
        issues.append(
            HealIssue(
                "keepalive_loss",
                "Keepalive timeout or 100% packet loss on tunnel peer",
                HealAction.bump_keepalive_restart,
            )
        )

    if _RTNETLINK_RE.search(logs_lower):
        issues.append(
            HealIssue(
                "rtnetlink",
                "Cannot assign tunnel IP (need NET_ADMIN on panel host)",
                HealAction.reassign_iface,
            )
        )

    if tunnel.role == HpxTunnelRole.iran and is_agent_managed(tunnel):
        if tunnel.agent_last_seen:
            stale = (dt.now(UTC) - tunnel.agent_last_seen).total_seconds()
            if stale > AGENT_STALE_SECONDS:
                issues.append(
                    HealIssue(
                        "agent_stale",
                        f"Iran agent silent for {int(stale)}s",
                        HealAction.agent_restart,
                    )
                )
            elif tunnel.status in {HpxTunnelStatus.error, HpxTunnelStatus.stopped}:
                issues.append(
                    HealIssue(
                        "agent_container_down",
                        "Iran tunnel down while agent is online",
                        HealAction.agent_start,
                    )
                )
        elif tunnel.status not in {HpxTunnelStatus.pending_claim, HpxTunnelStatus.stopped}:
            issues.append(
                HealIssue(
                    "agent_never_seen",
                    "Iran agent has not checked in",
                    HealAction.agent_restart,
                )
            )

    # Heuristic: duplicate kernel ICMP replies break keepalive
    if tunnel.packet_loss_pct is not None and tunnel.packet_loss_pct >= 100:
        if "icmp_echo_ignore" not in logs_lower:
            issues.append(
                HealIssue(
                    "icmp_kernel_reply",
                    "Kernel may be replying to ICMP alongside tunnel (set icmp_echo_ignore_all)",
                    HealAction.sysctl_icmp_ignore,
                )
            )

    return issues


async def apply_heal_action(
    tunnel: HpxTunnel,
    action: HealAction,
    *,
    password: str | None,
    force: bool = False,
) -> tuple[bool, str]:
    if not force:
        ok, reason = _heal_allowed(tunnel, action)
        if not ok:
            return False, reason or "heal skipped"

    if action == HealAction.none:
        return False, "no action"

    if action == HealAction.stop_conflicts:
        await stop_containers_using_interface(
            tunnel.interface, keep_name=tunnel.container_name or None
        )
        return True, "removed conflicting tunnel containers"

    if action == HealAction.sysctl_icmp_ignore:
        await apply_icmp_kernel_hardening()
        return True, "set net.ipv4.icmp_echo_ignore_all=1"

    if action == HealAction.reassign_iface:
        await apply_icmp_kernel_hardening()
        err = await _assign_interface_ip(
            tunnel.interface, tunnel.local_ip, tunnel.operating_mode, tunnel.mtu
        )
        if err:
            return False, err
        await _host_neigh_flush(tunnel.interface)
        return True, f"reassigned {tunnel.local_ip} on {tunnel.interface}"

    if action in {
        HealAction.restart_foreign,
        HealAction.bump_keepalive_restart,
        HealAction.unstuck_starting,
    }:
        if not password:
            return False, "password required for restart"
        if action == HealAction.bump_keepalive_restart and (tunnel.keepalive or 0) < MIN_KEEPALIVE:
            tunnel.keepalive = MIN_KEEPALIVE
        await apply_icmp_kernel_hardening()
        await stop_containers_using_interface(
            tunnel.interface, keep_name=tunnel.container_name or None
        )
        ok, err = await start_tunnel(tunnel, password)
        if not ok:
            return False, err or "restart failed"
        return True, "restarted tunnel container"

    if action == HealAction.agent_restart:
        tunnel.agent_command = "restart"
        tunnel.message = "Auto-heal: restart requested for Iran agent"
        return True, "queued agent restart"

    if action == HealAction.agent_start:
        tunnel.agent_command = "start"
        tunnel.message = "Auto-heal: start requested for Iran agent"
        return True, "queued agent start"

    return False, f"unknown action {action}"


async def _host_neigh_flush(interface: str) -> None:
    from app.services.hpx_tunnel.manager import _host_ip

    await _host_ip("neigh", "flush", "dev", interface, timeout=10)


async def evaluate_and_repair(
    tunnel: HpxTunnel,
    *,
    password: str | None,
    auto: bool = True,
) -> HealResult:
    result = HealResult()
    container_name = tunnel.container_name or f"hpx_tunnel_{tunnel.id}"
    logs = ""
    runtime = None

    if tunnel.role == HpxTunnelRole.foreign and not is_agent_managed(tunnel):
        runtime = await inspect_runtime(tunnel)
        logs = await get_container_logs(container_name, tail=40)

    issues = diagnose_tunnel(tunnel, runtime or _EmptyRuntime(), logs)
    result.issues = issues
    if not issues:
        return result

    priority = [
        HealAction.stop_conflicts,
        HealAction.sysctl_icmp_ignore,
        HealAction.unstuck_starting,
        HealAction.reassign_iface,
        HealAction.bump_keepalive_restart,
        HealAction.restart_foreign,
        HealAction.agent_restart,
        HealAction.agent_start,
    ]

    for heal_action in priority:
        matching = [i for i in issues if i.suggested_action == heal_action]
        if not matching:
            continue
        if auto and not tunnel.auto_heal_enabled:
            result.skipped_reason = "auto-heal disabled"
            break
        ok, msg = await apply_heal_action(
            tunnel, heal_action, password=password, force=not auto
        )
        if ok:
            result.actions_taken.append(msg)
            result.repaired = True
            tunnel.last_heal_at = dt.now(UTC)
            tunnel.last_heal_action = msg
            tunnel.heal_count_window = (tunnel.heal_count_window or 0) + 1
            logger.info("Healed tunnel %s: %s", tunnel.name, msg)
            break
        if not auto:
            result.skipped_reason = msg

    return result


@dataclass
class _EmptyRuntime:
    container_running: bool = False
    interface_up: bool = False
