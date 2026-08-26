"""Smart multi-step HPX tunnel doctor (allowlisted actions only — no free shell / no LLM)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime as dt

from app.db import AsyncSession
from app.db.crud.hpx_tunnel import get_hpx_tunnel_by_id, get_hpx_tunnels, is_agent_managed, update_hpx_tunnel
from app.db.crud.node import get_nodes
from app.db.models import HpxTunnel, HpxTunnelRole, HpxTunnelStatus
from app.models.node import NodeListQuery
from app.services.hpx_tunnel.healer import diagnose_tunnel
from app.services.hpx_tunnel.manager import (
    apply_icmp_kernel_hardening,
    get_container_logs,
    health_ping_target,
    inspect_runtime,
    peer_tunnel_ip,
    ping_host,
    preflight_panel_host,
    resolve_panel_public_ip,
    run_command,
    start_tunnel,
    stop_containers_using_interface,
)
from app.utils.logger import get_logger

logger = get_logger("hpx-tunnel-doctor")

AGENT_WAIT_SECONDS = 75
AGENT_POLL_EVERY = 3
VERIFY_ROUNDS = 4


@dataclass
class DoctorStep:
    title: str
    detail: str
    ok: bool = True


@dataclass
class DoctorReport:
    tunnel_id: int
    summary: str
    fixed: bool = False
    steps: list[DoctorStep] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    related_nodes: list[dict] = field(default_factory=list)


def _ip_host(value: str | None) -> str:
    return (value or "").split("/", 1)[0].strip()


async def _flush(db: AsyncSession) -> None:
    """Commit so Iran agent can see queued commands while we wait."""
    await db.commit()


async def _related_nodes(db: AsyncSession, remote_ip: str | None) -> list[dict]:
    if not remote_ip:
        return []
    host = _ip_host(remote_ip)
    nodes, _ = await get_nodes(db, NodeListQuery(offset=0, limit=200))
    related = []
    for node in nodes:
        addr = (node.address or "").strip()
        if addr == host or host in addr:
            related.append(
                {
                    "id": node.id,
                    "name": node.name,
                    "address": node.address,
                    "status": getattr(node.status, "value", str(node.status)),
                }
            )
    return related


async def _find_peer_tunnel(db: AsyncSession, tunnel: HpxTunnel) -> HpxTunnel | None:
    rows, _ = await get_hpx_tunnels(db, offset=0, limit=200)
    peer_ip = peer_tunnel_ip(tunnel.local_ip)
    for row in rows:
        if row.id == tunnel.id:
            continue
        if peer_ip and _ip_host(row.local_ip) == peer_ip:
            return row
        if row.role != tunnel.role and row.subnet == tunnel.subnet:
            return row
    return None


async def _resolve_panel_ip_strong(panel_url: str | None) -> tuple[str | None, str | None]:
    ip, src = await resolve_panel_public_ip(panel_url)
    if ip:
        return ip, src
    # Host default route source IP (often the public NIC on VPS).
    route = await run_command("ip", "-4", "route", "get", "1.1.1.1", timeout=5)
    if route.returncode == 0 and route.stdout:
        parts = route.stdout.split()
        if "src" in parts:
            candidate = parts[parts.index("src") + 1]
            try:
                import ipaddress

                addr = ipaddress.ip_address(candidate)
                if not addr.is_private and not addr.is_loopback:
                    return candidate, "default_route_src"
            except ValueError:
                pass
    return None, None


async def _wait_for_agent(db: AsyncSession, iran_id: int, report: DoctorReport) -> HpxTunnel | None:
    deadline = asyncio.get_event_loop().time() + AGENT_WAIT_SECONDS
    last: HpxTunnel | None = None
    while asyncio.get_event_loop().time() < deadline:
        last = await get_hpx_tunnel_by_id(db, iran_id)
        if last is None:
            return None
        # Agent cleared the command after ack → work done.
        if not last.agent_command:
            report.steps.append(
                DoctorStep(
                    "IRAN agent",
                    f"Agent acknowledged repair. status={last.status} msg={last.message or '-'}",
                    ok=True,
                )
            )
            return last
        await asyncio.sleep(AGENT_POLL_EVERY)
        await db.commit()

    last = await get_hpx_tunnel_by_id(db, iran_id)
    if last and last.agent_command:
        stale = None
        if last.agent_last_seen:
            stale = int((dt.now(UTC) - last.agent_last_seen).total_seconds())
        report.findings.append(
            f"Iran agent did not ack smart_fix within {AGENT_WAIT_SECONDS}s "
            f"(last_seen={stale}s ago, command still={last.agent_command}). "
            "On Iran VPS run: sudo hpx-tunnel-agent sync"
        )
        report.steps.append(
            DoctorStep(
                "IRAN agent",
                "Timeout waiting for agent — agent offline or timer not running on Iran VPS",
                ok=False,
            )
        )
    return last


async def _verify_peer(tunnel: HpxTunnel, report: DoctorReport) -> tuple[float | None, float | None, bool]:
    target = health_ping_target(tunnel)
    if not target:
        report.steps.append(DoctorStep("Verify", "No peer tunnel IP to ping", ok=False))
        return None, None, False

    best_latency = None
    best_loss = 100.0
    for round_i in range(1, VERIFY_ROUNDS + 1):
        latency, loss = await ping_host(target, count=4)
        if loss is not None and loss < best_loss:
            best_loss = loss
            best_latency = latency
        if loss is not None and loss < 100:
            report.steps.append(
                DoctorStep(
                    "Verify",
                    f"Round {round_i}/{VERIFY_ROUNDS}: peer {target} OK — {latency}ms, loss {loss}%",
                    ok=True,
                )
            )
            return latency, loss, True
        await asyncio.sleep(2)

    report.steps.append(
        DoctorStep(
            "Verify",
            f"Peer {target} still unreachable after {VERIFY_ROUNDS} rounds (loss={best_loss}%).",
            ok=False,
        )
    )
    return best_latency, best_loss, False


async def _ensure_foreign_up(
    db: AsyncSession,
    foreign: HpxTunnel,
    *,
    password: str,
    report: DoctorReport,
) -> HpxTunnel:
    preflight = await preflight_panel_host()
    if not preflight.get("ready"):
        msg = preflight.get("message") or "Panel Docker/NET_ADMIN not ready"
        report.findings.append(msg)
        report.steps.append(DoctorStep("Preflight", msg, ok=False))
        return foreign

    report.steps.append(DoctorStep("Preflight", "Linux + Docker + docker.sock + NET_ADMIN OK", ok=True))
    await apply_icmp_kernel_hardening()
    report.actions.append("panel icmp_echo_ignore_all=1")

    runtime = await inspect_runtime(foreign)
    logs = await get_container_logs(foreign.container_name or f"hpx_tunnel_{foreign.id}", tail=50)
    for issue in diagnose_tunnel(foreign, runtime, logs):
        report.findings.append(f"{issue.code}: {issue.message}")

    # Ensure sane defaults for ICMP keepalive.
    updates: dict = {}
    if (foreign.keepalive or 0) < 30:
        updates["keepalive"] = 30
    if not foreign.mtu or foreign.mtu > 1200:
        updates["mtu"] = 1000
    if updates:
        foreign = await update_hpx_tunnel(db, foreign, updates)
        report.actions.append(f"FOREIGN defaults {updates}")

    await stop_containers_using_interface(foreign.interface, keep_name=foreign.container_name or None)
    ok, err = await start_tunnel(foreign, password)
    if ok:
        foreign = await update_hpx_tunnel(
            db,
            foreign,
            {
                "status": HpxTunnelStatus.running,
                "message": "Doctor: FOREIGN running",
                "last_heal_at": dt.now(UTC),
                "last_heal_action": "doctor: restarted FOREIGN",
                "last_status_change": dt.now(UTC),
            },
        )
        report.actions.append("restarted FOREIGN on panel")
        report.steps.append(DoctorStep("FOREIGN", "Container restarted + IP/MTU applied", ok=True))
    else:
        foreign = await update_hpx_tunnel(
            db,
            foreign,
            {
                "status": HpxTunnelStatus.error,
                "message": err,
                "last_status_change": dt.now(UTC),
            },
        )
        report.findings.append(f"FOREIGN start failed: {err}")
        report.steps.append(DoctorStep("FOREIGN", err or "start failed", ok=False))
    await _flush(db)
    return foreign


async def run_smart_fix(
    db: AsyncSession,
    tunnel: HpxTunnel,
    *,
    password: str | None,
    panel_url: str | None = None,
    decrypt_password,
) -> DoctorReport:
    report = DoctorReport(tunnel_id=tunnel.id, summary="")
    peer = await _find_peer_tunnel(db, tunnel)
    panel_ip, panel_ip_src = await _resolve_panel_ip_strong(panel_url)

    foreign = tunnel if tunnel.role == HpxTunnelRole.foreign else peer
    iran = tunnel if tunnel.role == HpxTunnelRole.iran else peer

    report.related_nodes = await _related_nodes(db, (iran.remote_ip if iran else None) or tunnel.remote_ip)
    if report.related_nodes:
        names = ", ".join(f"{n['name']} ({n['status']})" for n in report.related_nodes)
        report.steps.append(DoctorStep("Nodes", f"Matched nodes: {names}", ok=True))
    else:
        report.steps.append(DoctorStep("Nodes", "No matching panel Node for this tunnel remote IP", ok=True))

    # --- Topology: force IRAN → panel IP when FOREIGN is on panel ---
    if foreign and not is_agent_managed(foreign) and iran:
        iran_remote = _ip_host(iran.remote_ip)
        if not panel_ip:
            report.findings.append("Could not detect panel public IP — cannot auto-align topology")
            report.steps.append(DoctorStep("Topology", f"Panel public IP unknown (src={panel_ip_src})", ok=False))
        elif iran_remote != panel_ip:
            report.findings.append(f"Topology mismatch: IRAN→{iran_remote} but panel={panel_ip}")
            iran = await update_hpx_tunnel(
                db,
                iran,
                {
                    "remote_ip": panel_ip,
                    "mtu": iran.mtu if iran.mtu and iran.mtu <= 1200 else 1000,
                    "keepalive": max(iran.keepalive or 0, 30),
                    "agent_command": "smart_fix",
                    "enabled": True,
                    "status": HpxTunnelStatus.starting,
                    "message": f"Doctor: remote_ip {iran_remote} → {panel_ip}",
                    "last_status_change": dt.now(UTC),
                },
            )
            report.actions.append(f"IRAN remote_ip {iran_remote} → {panel_ip}")
            report.steps.append(DoctorStep("Topology", f"Fixed: IRAN remote_ip now {panel_ip}", ok=True))
            await _flush(db)
        else:
            report.steps.append(DoctorStep("Topology", f"IRAN already points at panel {panel_ip}", ok=True))

    # --- FOREIGN on panel ---
    if foreign and not is_agent_managed(foreign):
        foreign_password = password if tunnel.id == foreign.id else await decrypt_password(db, foreign)
        foreign = await _ensure_foreign_up(db, foreign, password=foreign_password, report=report)

    # --- Queue + WAIT for Iran agent ---
    if iran and is_agent_managed(iran):
        stale_s = None
        if iran.agent_last_seen:
            stale_s = int((dt.now(UTC) - iran.agent_last_seen).total_seconds())
        if stale_s is not None and stale_s > 120:
            report.findings.append(f"Iran agent stale ({stale_s}s) — may be offline")
            report.steps.append(
                DoctorStep(
                    "IRAN agent",
                    f"Agent last seen {stale_s}s ago. Queuing smart_fix anyway; will wait for ack.",
                    ok=False,
                )
            )

        iran = await update_hpx_tunnel(
            db,
            iran,
            {
                "agent_command": "smart_fix",
                "enabled": True,
                "status": HpxTunnelStatus.starting,
                "message": "Doctor: waiting for Iran agent smart_fix",
                "last_status_change": dt.now(UTC),
                "last_heal_at": dt.now(UTC),
                "last_heal_action": "doctor: waiting agent smart_fix",
            },
        )
        report.actions.append("queued Iran agent smart_fix")
        await _flush(db)

        report.steps.append(
            DoctorStep(
                "IRAN agent",
                f"Waiting up to {AGENT_WAIT_SECONDS}s for agent to apply sysctl+restart…",
                ok=True,
            )
        )
        iran = await _wait_for_agent(db, iran.id, report) or iran
    elif iran and not is_agent_managed(iran):
        report.findings.append("IRAN has no agent — join token required on Iran VPS")
        report.steps.append(DoctorStep("IRAN agent", "Not claimed — cannot remote-fix", ok=False))

    # --- Verify (with retries). If fail once, restart FOREIGN again and re-check ---
    probe = foreign or tunnel
    latency, loss, ok = await _verify_peer(probe, report)
    if not ok and foreign and not is_agent_managed(foreign):
        report.steps.append(DoctorStep("Retry", "Peer still down — restarting FOREIGN once more", ok=True))
        foreign_password = password if tunnel.id == foreign.id else await decrypt_password(db, foreign)
        foreign = await _ensure_foreign_up(db, foreign, password=foreign_password, report=report)
        if iran and is_agent_managed(iran):
            iran = await update_hpx_tunnel(
                db,
                iran,
                {"agent_command": "smart_fix", "status": HpxTunnelStatus.starting, "last_status_change": dt.now(UTC)},
            )
            await _flush(db)
            iran = await _wait_for_agent(db, iran.id, report) or iran
        latency, loss, ok = await _verify_peer(foreign, report)

    if foreign:
        await update_hpx_tunnel(
            db,
            foreign,
            {
                "latency_ms": latency,
                "packet_loss_pct": loss,
                "last_health_check": dt.now(UTC),
                "status": HpxTunnelStatus.running if ok else HpxTunnelStatus.unhealthy,
            },
        )
    if iran and ok:
        await update_hpx_tunnel(
            db,
            iran,
            {
                "latency_ms": latency,
                "packet_loss_pct": loss,
                "status": HpxTunnelStatus.running,
                "message": "Doctor: peer path healthy",
            },
        )

    report.fixed = ok
    if ok:
        report.summary = (
            f"Doctor finished: tunnel path healthy (peer loss={loss}%, latency={latency}ms). "
            f"Actions: {', '.join(report.actions) or 'none'}."
        )
    else:
        tip = []
        if iran and is_agent_managed(iran) and iran.agent_command:
            tip.append("On Iran: sudo hpx-tunnel-agent sync")
        if panel_ip and iran and _ip_host(iran.remote_ip) != panel_ip:
            tip.append(f"IRAN remote_ip must be {panel_ip}")
        tip.append("Stop any extra FOREIGN container on other VPS (only one peer)")
        report.summary = (
            "Doctor could NOT verify peer ping yet. "
            + (" | ".join(tip))
            + f" | Actions tried: {', '.join(report.actions) or 'none'}"
        )

    await update_hpx_tunnel(
        db,
        tunnel,
        {
            "last_heal_at": dt.now(UTC),
            "last_heal_action": report.summary[:256],
            "message": report.summary[:1024],
        },
    )
    await _flush(db)
    logger.info("Doctor done tunnel=%s fixed=%s actions=%s", tunnel.name, report.fixed, report.actions)
    return report
