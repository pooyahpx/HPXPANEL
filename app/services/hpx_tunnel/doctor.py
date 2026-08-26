"""Smart multi-step HPX tunnel doctor (allowlisted actions only — no free shell / no LLM)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime as dt

from app.db import AsyncSession
from app.db.crud.hpx_tunnel import get_hpx_tunnels, is_agent_managed, update_hpx_tunnel
from app.db.crud.node import get_nodes
from app.db.models import HpxTunnel, HpxTunnelRole, HpxTunnelStatus
from app.models.node import NodeListQuery
from app.services.hpx_tunnel.healer import diagnose_tunnel, evaluate_and_repair
from app.services.hpx_tunnel.manager import (
    apply_icmp_kernel_hardening,
    get_container_logs,
    health_ping_target,
    inspect_runtime,
    peer_tunnel_ip,
    ping_host,
    preflight_panel_host,
    resolve_panel_public_ip,
    start_tunnel,
    stop_containers_using_interface,
)
from app.utils.logger import get_logger

logger = get_logger("hpx-tunnel-doctor")


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


async def _related_nodes(db: AsyncSession, remote_ip: str | None) -> list[dict]:
    if not remote_ip:
        return []
    host = _ip_host(remote_ip)
    nodes, _ = await get_nodes(db, NodeListQuery(offset=0, limit=200))
    related = []
    for node in nodes:
        addr = (node.address or "").strip()
        if addr == host or addr.endswith(f"/{host}") or host in addr:
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
        # Same password pair heuristic: iran/foreign with matching subnet
        if row.role != tunnel.role and row.subnet == tunnel.subnet:
            if tunnel.role == HpxTunnelRole.foreign and row.role == HpxTunnelRole.iran:
                return row
            if tunnel.role == HpxTunnelRole.iran and row.role == HpxTunnelRole.foreign:
                return row
    return None


async def run_smart_fix(
    db: AsyncSession,
    tunnel: HpxTunnel,
    *,
    password: str | None,
    panel_url: str | None = None,
    decrypt_password,
) -> DoctorReport:
    """
    Multi-step doctor:
    1) topology + nodes awareness
    2) panel preflight / FOREIGN runtime
    3) auto-align IRAN remote_ip to panel public IP when FOREIGN runs on panel
    4) harden + restart FOREIGN
    5) queue Iran agent smart_fix/restart
    6) verify peer ping
    """
    report = DoctorReport(tunnel_id=tunnel.id, summary="")
    peer = await _find_peer_tunnel(db, tunnel)
    panel_ip, panel_ip_src = await resolve_panel_public_ip(panel_url)
    preflight = await preflight_panel_host()
    report.related_nodes = await _related_nodes(db, tunnel.remote_ip or (peer.remote_ip if peer else None))

    if report.related_nodes:
        names = ", ".join(f"{n['name']} ({n['status']})" for n in report.related_nodes)
        report.findings.append(f"Remote IP matches panel node(s): {names}")
        report.steps.append(DoctorStep("Nodes", f"Matched node inventory: {names}", ok=True))
    else:
        report.steps.append(
            DoctorStep(
                "Nodes",
                "No panel Node matches this tunnel remote IP (ICMP tunnel is independent of Xray nodes).",
                ok=True,
            )
        )

    # --- Topology ---
    foreign = tunnel if tunnel.role == HpxTunnelRole.foreign else peer
    iran = tunnel if tunnel.role == HpxTunnelRole.iran else peer

    if foreign and not is_agent_managed(foreign) and iran and iran.remote_ip:
        iran_remote = _ip_host(iran.remote_ip)
        if panel_ip and iran_remote and iran_remote != panel_ip:
            report.findings.append(
                f"Topology mismatch: IRAN remote_ip={iran_remote} but panel public IP={panel_ip} "
                f"(FOREIGN on panel will never peer with this IRAN)."
            )
            report.steps.append(
                DoctorStep(
                    "Topology",
                    f"Aligning IRAN remote_ip {iran_remote} → {panel_ip} (panel FOREIGN peer).",
                    ok=True,
                )
            )
            iran = await update_hpx_tunnel(
                db,
                iran,
                {
                    "remote_ip": panel_ip,
                    "agent_command": "smart_fix",
                    "message": f"Doctor: remote_ip corrected to panel {panel_ip}",
                    "status": HpxTunnelStatus.starting,
                    "last_status_change": dt.now(UTC),
                },
            )
            report.actions.append(f"set IRAN remote_ip={panel_ip}")
            report.actions.append("queued Iran agent smart_fix")
        elif panel_ip and iran_remote == panel_ip:
            report.steps.append(
                DoctorStep("Topology", f"IRAN remote_ip already points at panel ({panel_ip}).", ok=True)
            )
        else:
            report.steps.append(
                DoctorStep(
                    "Topology",
                    f"Panel public IP unknown (src={panel_ip_src}); skipped remote_ip auto-align.",
                    ok=False,
                )
            )
    else:
        report.steps.append(DoctorStep("Topology", "Checked foreign/iran pairing.", ok=True))

    # --- Panel preflight (FOREIGN host) ---
    if foreign and not is_agent_managed(foreign):
        if not preflight.get("ready"):
            report.findings.append(preflight.get("message") or "Panel host not ready for FOREIGN Docker")
            report.steps.append(
                DoctorStep("Preflight", preflight.get("message") or "Panel Docker/NET_ADMIN not ready", ok=False)
            )
        else:
            report.steps.append(DoctorStep("Preflight", "Linux + Docker + docker.sock + NET_ADMIN OK", ok=True))

        await apply_icmp_kernel_hardening()
        report.actions.append("panel icmp_echo_ignore_all=1")

        runtime = await inspect_runtime(foreign)
        logs = await get_container_logs(foreign.container_name or f"hpx_tunnel_{foreign.id}", tail=40)
        issues = diagnose_tunnel(foreign, runtime, logs)
        if issues:
            report.findings.extend(f"{i.code}: {i.message}" for i in issues)

        foreign_password = password if tunnel.id == foreign.id else None
        if foreign_password is None:
            foreign_password = await decrypt_password(db, foreign)

        await stop_containers_using_interface(foreign.interface, keep_name=foreign.container_name or None)
        ok, err = await start_tunnel(foreign, foreign_password)
        if ok:
            foreign = await update_hpx_tunnel(
                db,
                foreign,
                {
                    "status": HpxTunnelStatus.running,
                    "message": "Doctor: FOREIGN restarted",
                    "last_heal_at": dt.now(UTC),
                    "last_heal_action": "doctor: restarted FOREIGN",
                    "last_status_change": dt.now(UTC),
                },
            )
            report.actions.append("restarted FOREIGN on panel")
            report.steps.append(DoctorStep("FOREIGN", "Container restarted + IP assigned", ok=True))
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

        # Fall back to rule healer for leftover issues
        heal = await evaluate_and_repair(foreign, password=foreign_password, auto=False)
        if heal.actions_taken:
            report.actions.extend(heal.actions_taken)

    # --- Iran agent ---
    if iran and is_agent_managed(iran):
        iran = await update_hpx_tunnel(
            db,
            iran,
            {
                "agent_command": "smart_fix",
                "status": HpxTunnelStatus.starting,
                "message": "Doctor: smart_fix queued for Iran agent",
                "last_status_change": dt.now(UTC),
                "last_heal_at": dt.now(UTC),
                "last_heal_action": "doctor: queued agent smart_fix",
            },
        )
        report.actions.append("queued Iran agent smart_fix (sysctl + conflict cleanup + restart)")
        report.steps.append(
            DoctorStep(
                "IRAN agent",
                "Queued smart_fix — agent applies sysctl, stops conflicts, restarts within ~30s",
                ok=True,
            )
        )
    elif iran and not is_agent_managed(iran):
        report.findings.append("IRAN tunnel has no agent claim — generate join token on Iran VPS")
        report.steps.append(DoctorStep("IRAN agent", "Not claimed — cannot remote-fix", ok=False))

    # --- Verify ---
    await asyncio.sleep(2)
    target = health_ping_target(foreign or tunnel)
    if target:
        latency, loss = await ping_host(target, count=3)
        if foreign:
            await update_hpx_tunnel(
                db,
                foreign,
                {"latency_ms": latency, "packet_loss_pct": loss, "last_health_check": dt.now(UTC)},
            )
        if loss is not None and loss < 100:
            report.steps.append(
                DoctorStep("Verify", f"Peer {target} reachable — latency={latency}ms loss={loss}%", ok=True)
            )
            report.fixed = True
        else:
            report.steps.append(
                DoctorStep(
                    "Verify",
                    f"Peer {target} still unreachable (loss={loss}). "
                    "Wait for Iran agent smart_fix (~30s) then refresh. "
                    "If IRAN still points at another VPS, stop that FOREIGN and keep only panel FOREIGN.",
                    ok=False,
                )
            )
            # Partial success if we at least restarted / reconfigured
            report.fixed = bool(report.actions)
    else:
        report.fixed = bool(report.actions)
        report.steps.append(DoctorStep("Verify", "No peer tunnel IP to ping", ok=False))

    if report.fixed and all(s.ok for s in report.steps if s.title == "Verify"):
        report.summary = "Doctor repaired the tunnel path and peer ping succeeded."
    elif report.actions:
        report.summary = (
            "Doctor applied fixes and queued Iran agent repair. "
            "Refresh in ~30–60s; if still 100% loss, IRAN remote must be the panel public IP only."
        )
        report.fixed = True
    else:
        report.summary = "Doctor found issues but could not apply a repair. Check findings."

    # Persist heal markers on the requested tunnel
    await update_hpx_tunnel(
        db,
        tunnel,
        {
            "last_heal_at": dt.now(UTC),
            "last_heal_action": report.summary[:256],
            "message": report.summary[:1024],
        },
    )
    logger.info("Doctor finished tunnel %s fixed=%s actions=%s", tunnel.name, report.fixed, report.actions)
    return report
