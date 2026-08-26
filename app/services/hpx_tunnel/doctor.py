"""Smart multi-step HPX tunnel doctor (allowlisted actions — no free shell).

Topology modes:
- panel_foreign: IRAN.remote_ip == panel public IP → heal panel FOREIGN + Iran agent
- node_foreign:  IRAN.remote_ip matches a panel Node → heal Iran agent only; never overwrite remote_ip
- external:      other remote IP → heal Iran agent only; never overwrite remote_ip
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime as dt
from enum import Enum

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


class TopologyMode(str, Enum):
    panel_foreign = "panel_foreign"
    node_foreign = "node_foreign"
    external = "external"
    unknown = "unknown"


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


@dataclass
class NodeInfo:
    id: int
    name: str
    address: str
    status: str


def _ip_host(value: str | None) -> str:
    return (value or "").split("/", 1)[0].strip()


async def _flush(db: AsyncSession) -> None:
    await db.commit()


async def _load_nodes(db: AsyncSession) -> list[NodeInfo]:
    nodes, _ = await get_nodes(db, NodeListQuery(offset=0, limit=500))
    out: list[NodeInfo] = []
    for node in nodes:
        out.append(
            NodeInfo(
                id=node.id,
                name=node.name,
                address=(node.address or "").strip(),
                status=getattr(node.status, "value", str(node.status)),
            )
        )
    return out


def _match_nodes(nodes: list[NodeInfo], remote_ip: str | None) -> list[NodeInfo]:
    host = _ip_host(remote_ip)
    if not host:
        return []
    matched = []
    for node in nodes:
        addr = node.address
        if not addr:
            continue
        if addr == host or host == _ip_host(addr) or host in addr or addr in host:
            matched.append(node)
    return matched


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


def _detect_topology(
    *,
    iran: HpxTunnel | None,
    panel_ip: str | None,
    matched_nodes: list[NodeInfo],
) -> TopologyMode:
    if not iran:
        return TopologyMode.unknown
    remote = _ip_host(iran.remote_ip)
    if matched_nodes:
        return TopologyMode.node_foreign
    if panel_ip and remote and remote == panel_ip:
        return TopologyMode.panel_foreign
    if remote:
        return TopologyMode.external
    return TopologyMode.unknown


async def _wait_for_agent(db: AsyncSession, iran_id: int, report: DoctorReport) -> HpxTunnel | None:
    deadline = asyncio.get_event_loop().time() + AGENT_WAIT_SECONDS
    while asyncio.get_event_loop().time() < deadline:
        last = await get_hpx_tunnel_by_id(db, iran_id)
        if last is None:
            return None
        if not last.agent_command:
            report.steps.append(
                DoctorStep(
                    "IRAN agent",
                    f"Agent ack OK — status={last.status} msg={last.message or '-'}",
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
            f"Iran agent did not ack within {AGENT_WAIT_SECONDS}s "
            f"(last_seen={stale}s ago). On Iran: sudo hpx-tunnel-agent sync"
        )
        report.steps.append(DoctorStep("IRAN agent", "Timeout waiting for agent ack", ok=False))
    return last


async def _verify_peer(tunnel: HpxTunnel, report: DoctorReport) -> tuple[float | None, float | None, bool]:
    target = health_ping_target(tunnel)
    if not target:
        report.steps.append(DoctorStep("Verify", "No peer tunnel IP to ping from this host", ok=False))
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
                    f"Round {round_i}: peer {target} OK — {latency}ms loss={loss}%",
                    ok=True,
                )
            )
            return latency, loss, True
        await asyncio.sleep(2)

    report.steps.append(
        DoctorStep(
            "Verify",
            f"Peer {target} unreachable after {VERIFY_ROUNDS} rounds (loss={best_loss}%). "
            "If FOREIGN runs on a Node (not panel), panel cannot ping 10.200.200.x — "
            "trust Iran agent heartbeat instead.",
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

    report.steps.append(DoctorStep("Preflight", "Panel host ready for FOREIGN Docker", ok=True))
    await apply_icmp_kernel_hardening()
    report.actions.append("panel icmp_echo_ignore_all=1")

    runtime = await inspect_runtime(foreign)
    logs = await get_container_logs(foreign.container_name or f"hpx_tunnel_{foreign.id}", tail=50)
    for issue in diagnose_tunnel(foreign, runtime, logs):
        report.findings.append(f"{issue.code}: {issue.message}")

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
                "message": "Doctor: FOREIGN running on panel",
                "last_heal_at": dt.now(UTC),
                "last_heal_action": "doctor: restarted FOREIGN",
                "last_status_change": dt.now(UTC),
            },
        )
        report.actions.append("restarted FOREIGN on panel")
        report.steps.append(DoctorStep("FOREIGN", "Panel FOREIGN restarted", ok=True))
    else:
        foreign = await update_hpx_tunnel(
            db,
            foreign,
            {"status": HpxTunnelStatus.error, "message": err, "last_status_change": dt.now(UTC)},
        )
        report.findings.append(f"FOREIGN start failed: {err}")
        report.steps.append(DoctorStep("FOREIGN", err or "start failed", ok=False))
    await _flush(db)
    return foreign


async def _queue_agent_smart_fix(db: AsyncSession, iran: HpxTunnel, report: DoctorReport) -> HpxTunnel:
    iran = await update_hpx_tunnel(
        db,
        iran,
        {
            "agent_command": "smart_fix",
            "enabled": True,
            "status": HpxTunnelStatus.starting,
            "message": "Doctor: Iran agent smart_fix queued",
            "last_status_change": dt.now(UTC),
            "last_heal_at": dt.now(UTC),
            "last_heal_action": "doctor: waiting agent smart_fix",
        },
    )
    report.actions.append("queued Iran agent smart_fix")
    await _flush(db)
    report.steps.append(DoctorStep("IRAN agent", f"Waiting up to {AGENT_WAIT_SECONDS}s for agent smart_fix…", ok=True))
    return await _wait_for_agent(db, iran.id, report) or iran


async def run_smart_fix(
    db: AsyncSession,
    tunnel: HpxTunnel,
    *,
    password: str | None,
    panel_url: str | None = None,
    decrypt_password,
) -> DoctorReport:
    report = DoctorReport(tunnel_id=tunnel.id, summary="")
    all_nodes = await _load_nodes(db)
    peer = await _find_peer_tunnel(db, tunnel)
    panel_ip, panel_ip_src = await _resolve_panel_ip_strong(panel_url)

    foreign = tunnel if tunnel.role == HpxTunnelRole.foreign else peer
    iran = tunnel if tunnel.role == HpxTunnelRole.iran else peer

    # Inventory for UI
    report.related_nodes = [
        {"id": n.id, "name": n.name, "address": n.address, "status": n.status} for n in all_nodes[:50]
    ]
    node_list_txt = ", ".join(f"{n.name}={n.address}[{n.status}]" for n in all_nodes[:20]) or "(no nodes)"
    report.steps.append(
        DoctorStep(
            "Nodes inventory",
            f"Panel has {len(all_nodes)} node(s). Panel public IP={panel_ip or '?'} ({panel_ip_src}). "
            f"Sample: {node_list_txt}",
            ok=True,
        )
    )

    matched = _match_nodes(all_nodes, iran.remote_ip if iran else tunnel.remote_ip)
    mode = _detect_topology(iran=iran, panel_ip=panel_ip, matched_nodes=matched)

    if matched:
        names = ", ".join(f"{n.name} ({n.address}, {n.status})" for n in matched)
        report.steps.append(
            DoctorStep(
                "Topology",
                f"Mode=node_foreign — IRAN remote_ip intentionally points at Node: {names}. "
                "Will NOT overwrite remote_ip with panel IP. FOREIGN must run on that Node host.",
                ok=True,
            )
        )
        report.findings.append(f"Using Node as FOREIGN endpoint: {names}")
    elif mode == TopologyMode.panel_foreign:
        report.steps.append(
            DoctorStep(
                "Topology",
                f"Mode=panel_foreign — IRAN remote_ip equals panel public IP ({panel_ip}).",
                ok=True,
            )
        )
    elif mode == TopologyMode.external:
        report.steps.append(
            DoctorStep(
                "Topology",
                f"Mode=external — IRAN remote_ip={_ip_host(iran.remote_ip if iran else None)} "
                f"(not panel, not a known Node). Preserving remote_ip.",
                ok=True,
            )
        )
    else:
        report.steps.append(DoctorStep("Topology", "Could not classify topology", ok=False))

    # CRITICAL: never force panel IP when user chose a Node / external IP
    if mode in {TopologyMode.node_foreign, TopologyMode.external}:
        # Panel-side FOREIGN is NOT the peer for this IRAN — don't restart it as heal.
        if foreign and not is_agent_managed(foreign) and tunnel.role == HpxTunnelRole.foreign:
            report.steps.append(
                DoctorStep(
                    "FOREIGN on panel",
                    "This panel FOREIGN is not the peer for your Node-targeted IRAN. "
                    "Skipping panel FOREIGN restart. Run FOREIGN Docker on the Node VPS instead "
                    "(listen 0.0.0.0, same password, local_ip 10.200.200.1).",
                    ok=True,
                )
            )
        elif foreign and not is_agent_managed(foreign):
            report.steps.append(
                DoctorStep(
                    "FOREIGN on panel",
                    "IRAN peers with a Node/external IP — left panel FOREIGN alone.",
                    ok=True,
                )
            )

        if iran and is_agent_managed(iran):
            # Ensure keepalive/mtu sane without touching remote_ip
            updates: dict = {}
            if (iran.keepalive or 0) < 30:
                updates["keepalive"] = 30
            if not iran.mtu or iran.mtu > 1200:
                updates["mtu"] = 1000
            if updates:
                iran = await update_hpx_tunnel(db, iran, updates)
                report.actions.append(f"IRAN defaults {updates}")
                await _flush(db)

            stale_s = None
            if iran.agent_last_seen:
                stale_s = int((dt.now(UTC) - iran.agent_last_seen).total_seconds())
            if stale_s is not None and stale_s > 120:
                report.findings.append(f"Iran agent stale ({stale_s}s)")

            iran = await _queue_agent_smart_fix(db, iran, report)

            # For node/external mode, panel cannot reliably ping tunnel peer.
            # Success = agent cleared command and reports running / loss < 100 from heartbeat.
            iran = await get_hpx_tunnel_by_id(db, iran.id) or iran
            agent_ok = (
                not iran.agent_command
                and iran.status in {HpxTunnelStatus.running, HpxTunnelStatus.unhealthy}
                and (iran.packet_loss_pct is None or iran.packet_loss_pct < 100)
            )
            # After smart_fix, give heartbeat a moment
            await asyncio.sleep(3)
            iran = await get_hpx_tunnel_by_id(db, iran.id) or iran
            if iran.status == HpxTunnelStatus.running and (iran.packet_loss_pct is None or iran.packet_loss_pct < 100):
                agent_ok = True
            elif not iran.agent_command and iran.status == HpxTunnelStatus.running:
                # Agent restarted; loss may still update next heartbeat
                agent_ok = True
                report.steps.append(
                    DoctorStep(
                        "Verify",
                        "Agent restarted FOREIGN path on Iran. Peer loss will refresh on next heartbeat (~15–30s).",
                        ok=True,
                    )
                )

            report.fixed = bool(agent_ok or (not iran.agent_command and iran.status == HpxTunnelStatus.running))
            if report.fixed:
                report.summary = (
                    f"Doctor OK (node/external mode): kept remote_ip={iran.remote_ip}, "
                    f"Iran agent smart_fix done, status={iran.status}. "
                    f"FOREIGN must be running on {_ip_host(iran.remote_ip)} "
                    f"(Node: {matched[0].name if matched else 'external host'})."
                )
            else:
                report.summary = (
                    f"Doctor could not finish Iran agent repair. remote_ip kept as {iran.remote_ip}. "
                    f"Confirm FOREIGN Docker is running on that host (not on panel). "
                    f"On Iran: sudo hpx-tunnel-agent sync. Actions: {', '.join(report.actions) or 'none'}"
                )

        elif iran and not is_agent_managed(iran):
            report.findings.append("IRAN has no agent claim")
            report.steps.append(DoctorStep("IRAN agent", "Not claimed — generate join token", ok=False))
            report.summary = "IRAN agent not claimed — cannot remote-fix Node tunnel."
        else:
            report.summary = "No IRAN tunnel in pair — nothing to smart-fix for Node mode."

    else:
        # panel_foreign mode — heal panel FOREIGN + agent
        if foreign and not is_agent_managed(foreign):
            foreign_password = password if tunnel.id == foreign.id else await decrypt_password(db, foreign)
            foreign = await _ensure_foreign_up(db, foreign, password=foreign_password, report=report)

        if iran and is_agent_managed(iran):
            # Only align to panel IP in panel_foreign mode when remote empty/wrong private junk — NOT when node matched
            if panel_ip and _ip_host(iran.remote_ip) != panel_ip and mode == TopologyMode.panel_foreign:
                # already panel mode only if equal — skip overwrite
                pass
            iran = await _queue_agent_smart_fix(db, iran, report)

        probe = foreign or tunnel
        latency, loss, ok = await _verify_peer(probe, report)
        if not ok and foreign and not is_agent_managed(foreign):
            foreign_password = password if tunnel.id == foreign.id else await decrypt_password(db, foreign)
            foreign = await _ensure_foreign_up(db, foreign, password=foreign_password, report=report)
            if iran and is_agent_managed(iran):
                iran = await _queue_agent_smart_fix(db, iran, report)
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
        report.fixed = ok
        report.summary = (
            f"Doctor finished panel_foreign mode: peer loss={loss}% latency={latency}ms."
            if ok
            else f"Doctor failed panel_foreign verify. Actions: {', '.join(report.actions) or 'none'}"
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
    logger.info(
        "Doctor done tunnel=%s mode=%s fixed=%s actions=%s",
        tunnel.name,
        mode.value,
        report.fixed,
        report.actions,
    )
    return report
