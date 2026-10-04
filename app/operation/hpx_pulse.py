import hashlib
import json
import secrets
from datetime import UTC, datetime as dt, timedelta as td

from sqlalchemy.exc import IntegrityError

from app.core.hosts import host_manager
from app.db import AsyncSession
from app.db.crud.general import get_jwt_secret_key
from app.db.crud.host import get_hosts
from app.db.crud.hpx_pulse import (
    create_hpx_pulse,
    delete_hpx_pulse,
    get_hpx_pulse_by_agent_key_hash,
    get_hpx_pulse_by_id,
    get_hpx_pulse_by_join_token_hash,
    get_hpx_pulses,
    set_join_token,
    update_hpx_pulse,
)
from app.db.models import HpxPulse, HpxPulseStatus
from app.models.admin import AdminDetails
from app.models.hpx_pulse import (
    HpxPulseActionResponse,
    HpxPulseAgentAckRequest,
    HpxPulseAgentBootstrap,
    HpxPulseAgentClaimRequest,
    HpxPulseAgentConfigResponse,
    HpxPulseAgentHeartbeatRequest,
    HpxPulseCreate,
    HpxPulseDiagnoseResponse,
    HpxPulsePathPingRequest,
    HpxPulsePathPingResponse,
    HpxPulseResponse,
    HpxPulsesResponse,
    HpxPulseUpdate,
    PulseAdviseRequest,
    PulseAdviseResponse,
)
from app.operation import BaseOperation
from app.services.hpx_pulse.advisor import advise, profile_meta
from app.services.hpx_pulse.config_linker import rewrite_host_addresses_to_iran, scan_hosts_for_pulse
from app.services.hpx_pulse.diagnose import (
    PulseDiagCheck,
    checks_from_linked_hosts,
    diagnose_pulse_record,
    diagnose_summary,
)
from app.services.hpx_pulse.engine_mirror import agent_assets_base, engine_version
from app.services.hpx_pulse.tcp_autofix import extreme_profile_update, should_autofix_tcp_extreme
from app.utils.logger import get_logger

logger = get_logger("hpx-pulse")
from app.services.hpx_pulse.tunnel_render import mint_tunnel_token, render_for_side
from app.utils.crypto import decrypt_secret, encrypt_secret, hash_api_key
from app.utils.helpers import resolve_panel_base_url

JOIN_TOKEN_TTL_HOURS = 24
GITHUB_AGENT_SCRIPT = "https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/scripts/hpx-pulse-agent.sh"
_JOIN_CURL = "--http1.1 --connect-timeout 20 --max-time 120 -fsSL"


def _mint_token(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def _config_hash(toml: str, side: str, pulse_id: int) -> str:
    canonical = json.dumps({"toml": toml, "side": side, "pulse_id": pulse_id}, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _panel_base(panel_url: str | None) -> str:
    return (panel_url or "https://YOUR_PANEL_HOST").rstrip("/")


def _url_with_host(panel_url: str | None, host: str) -> str:
    """Keep scheme/port from panel_url but replace hostname with host (usually public IP)."""
    from urllib.parse import urlparse, urlunparse

    raw = _panel_base(panel_url)
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    scheme = parsed.scheme or "https"
    port = parsed.port
    if port and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
        netloc = f"{host}:{port}"
    else:
        netloc = host
    return urlunparse((scheme, netloc, "", "", "", ""))


def _build_join_command_github(
    panel_url: str | None,
    token: str,
    side: str,
    *,
    insecure: bool = False,
) -> str:
    base = _panel_base(panel_url)
    env = "HPX_PREFER_GITHUB=1 " if side == "iran" else ""
    insecure_flag = " --insecure" if insecure else ""
    return (
        f"curl {_JOIN_CURL} \\\n"
        f"  {GITHUB_AGENT_SCRIPT} | \\\n"
        f"  sudo env {env}bash -s -- join {token} \\\n"
        f"  --panel-url {base} --side {side}{insecure_flag}"
    )


def _build_join_command_panel(panel_url: str | None, token: str, side: str, *, insecure: bool = False) -> str:
    base = _panel_base(panel_url)
    panel_script = f"{base}/api/hpx_pulse/agent/hpx-pulse-agent.sh"
    runner = "sudo env HPX_PREFER_GITHUB=1 bash" if side == "iran" else "sudo bash"
    insecure_flag = " --insecure" if insecure else ""
    return (
        f"curl {_JOIN_CURL} \\\n"
        f"  {panel_script} | \\\n"
        f"  {runner} -s -- join {token} \\\n"
        f"  --panel-url {base} --side {side}{insecure_flag}"
    )


def _build_join_command(panel_url: str | None, token: str, side: str) -> str:
    """Primary install command (GitHub bootstrap — works from Iran)."""
    return _build_join_command_github(panel_url, token, side)


def _pulse_status(db_pulse: HpxPulse) -> str:
    iran = bool(db_pulse.iran_agent_key_hash)
    abroad = bool(db_pulse.abroad_agent_key_hash)
    if iran and abroad:
        return db_pulse.status.value if hasattr(db_pulse.status, "value") else str(db_pulse.status)
    if iran or abroad:
        return HpxPulseStatus.partial.value
    return HpxPulseStatus.pending_claim.value


def _to_response(db_pulse: HpxPulse) -> HpxPulseResponse:
    advice = None
    if db_pulse.advice_json:
        try:
            advice = PulseAdviseResponse.model_validate(db_pulse.advice_json)
        except Exception:
            advice = None
    data = {
        "id": db_pulse.id,
        "name": db_pulse.name,
        "status": _pulse_status(db_pulse),
        "enabled": db_pulse.enabled,
        "engine": db_pulse.engine,
        "profile_id": db_pulse.profile_id,
        "goal": db_pulse.goal,
        "tunnel_mode": db_pulse.tunnel_mode,
        "carrier": db_pulse.carrier,
        "preset": db_pulse.preset,
        "iran_public_ip": db_pulse.iran_public_ip,
        "abroad_public_ip": db_pulse.abroad_public_ip,
        "control_port": db_pulse.control_port,
        "local_ip_iran": db_pulse.local_ip_iran,
        "local_ip_abroad": db_pulse.local_ip_abroad,
        "port_forwards": db_pulse.port_forwards or [],
        "domain": db_pulse.domain,
        "sni_hint": db_pulse.sni_hint,
        "note": db_pulse.note,
        "advice": advice,
        "iran_claimed": bool(db_pulse.iran_agent_key_hash),
        "abroad_claimed": bool(db_pulse.abroad_agent_key_hash),
        "iran_agent_host": db_pulse.iran_agent_host,
        "abroad_agent_host": db_pulse.abroad_agent_host,
        "iran_agent_last_seen": db_pulse.iran_agent_last_seen,
        "abroad_agent_last_seen": db_pulse.abroad_agent_last_seen,
        "iran_join_expires_at": db_pulse.iran_join_token_expires_at if not db_pulse.iran_agent_key_hash else None,
        "abroad_join_expires_at": db_pulse.abroad_join_token_expires_at if not db_pulse.abroad_agent_key_hash else None,
        "message": db_pulse.message,
        "latency_ms": db_pulse.latency_ms,
        "packet_loss_pct": db_pulse.packet_loss_pct,
        "auto_restart_interval_minutes": db_pulse.auto_restart_interval_minutes,
        "last_auto_restart_at": db_pulse.last_auto_restart_at,
        "auto_heal_enabled": db_pulse.auto_heal_enabled,
        "last_heal_at": db_pulse.last_heal_at,
        "last_heal_action": db_pulse.last_heal_action,
        "last_health_check": db_pulse.last_health_check,
        "backup_pulse_id": db_pulse.backup_pulse_id,
        "auto_failover": db_pulse.auto_failover,
        "auto_failback": db_pulse.auto_failback,
        "failover_active": db_pulse.failover_active,
        "priority": db_pulse.priority,
        "last_failover_at": db_pulse.last_failover_at,
        "created_at": db_pulse.created_at,
        "path_ping": (
            (db_pulse.diag_report or {}).get("path_ping") if isinstance(db_pulse.diag_report, dict) else None
        ),
    }
    return HpxPulseResponse.model_validate(data)


def _desired_status(db_pulse: HpxPulse) -> str:
    if not db_pulse.enabled:
        return HpxPulseStatus.stopped.value
    return HpxPulseStatus.running.value


class HpxPulseOperation(BaseOperation):
    async def _panel_url(self, request_base: str | None = None) -> str | None:
        return await resolve_panel_base_url(prefer=request_base)

    async def _secret_key(self, db: AsyncSession) -> str:
        return await get_jwt_secret_key(db)

    async def _encrypt_token(self, db: AsyncSession, token: str) -> str:
        secret = await self._secret_key(db)
        return encrypt_secret(token, secret)

    async def _decrypt_token(self, db: AsyncSession, db_pulse: HpxPulse) -> str:
        secret = await self._secret_key(db)
        return decrypt_secret(db_pulse.token_encrypted, secret)

    async def advise_pulse(
        self, model: PulseAdviseRequest, *, domain: str | None = None, sni_hint: str | None = None
    ) -> PulseAdviseResponse:
        return advise(model, domain=domain, sni_hint=sni_hint)

    async def _iran_join_commands(self, panel_url: str | None, iran_token: str) -> tuple[str, str]:
        """Iran primary = domain URL; alt = public IP + --insecure (SNI/TLS filter bypass)."""
        from app.services.hpx_tunnel.manager import resolve_panel_public_ip

        domain_cmd = _build_join_command_github(panel_url, iran_token, "iran")
        ip, _src = await resolve_panel_public_ip(panel_url)
        if ip:
            ip_url = _url_with_host(panel_url, ip)
            return (
                domain_cmd,
                _build_join_command_github(ip_url, iran_token, "iran", insecure=True),
            )
        # No public IP resolved — domain primary; insecure domain as fallback.
        return (
            domain_cmd,
            _build_join_command_github(panel_url, iran_token, "iran", insecure=True),
        )

    async def _issue_join_tokens(
        self, db: AsyncSession, db_pulse: HpxPulse, *, panel_url: str | None
    ) -> tuple[str, str, str, str, str, str, dt]:
        expires_at = dt.now(UTC) + td(hours=JOIN_TOKEN_TTL_HOURS)
        iran_token = _mint_token("hpxpi")
        abroad_token = _mint_token("hpxpa")
        set_join_token(db_pulse, side="iran", token=iran_token, expires_at=expires_at)
        set_join_token(db_pulse, side="abroad", token=abroad_token, expires_at=expires_at)
        db_pulse.iran_agent_key_hash = None
        db_pulse.abroad_agent_key_hash = None
        db_pulse.iran_agent_claimed_at = None
        db_pulse.abroad_agent_claimed_at = None
        db_pulse.iran_agent_host = None
        db_pulse.abroad_agent_host = None
        db_pulse.iran_agent_command = "start"
        db_pulse.abroad_agent_command = "start"
        db_pulse.status = HpxPulseStatus.pending_claim
        db_pulse.message = "Waiting for Iran and abroad agents"
        db_pulse.last_status_change = dt.now(UTC)
        await db.flush()
        iran_cmd, iran_cmd_alt = await self._iran_join_commands(panel_url, iran_token)
        abroad_cmd = _build_join_command_panel(panel_url, abroad_token, "abroad")
        abroad_cmd_alt = _build_join_command_github(panel_url, abroad_token, "abroad")
        return iran_token, iran_cmd, iran_cmd_alt, abroad_token, abroad_cmd, abroad_cmd_alt, expires_at

    async def create_pulse(
        self,
        db: AsyncSession,
        *,
        admin: AdminDetails,
        model: HpxPulseCreate,
        panel_url: str | None = None,
    ) -> HpxPulseActionResponse:
        _ = admin
        duplicates, _ = await get_hpx_pulses(db, offset=0, limit=1, name=model.name)
        if duplicates:
            await self.raise_error(message="Pulse name already exists", code=409)

        same_iran_warning = ""
        if model.iran_public_ip:
            peers, _ = await get_hpx_pulses(db, offset=0, limit=50)
            for peer in peers:
                if peer.iran_public_ip == model.iran_public_ip and peer.iran_agent_key_hash:
                    same_iran_warning = (
                        " — same Iran IP already has an active agent; "
                        "each pulse needs its own control port and non-overlapping forward ports, "
                        "or add forwards to the existing pulse"
                    )
                    break

        advise_req = PulseAdviseRequest(
            cpu_cores=model.cpu_cores,
            ram_mb=model.ram_mb,
            udp_reachable=model.udp_reachable,
            packet_loss_pct=model.packet_loss_pct,
            goal=model.goal,
        )
        advice = advise(
            advise_req,
            domain=model.domain,
            sni_hint=model.sni_hint,
            profile_override=model.profile_id,
        )
        meta = profile_meta(advice.recommended_profile_id)
        chosen = next((p for p in advice.profiles if p.profile_id == advice.recommended_profile_id), advice.profiles[0])

        tunnel_token = mint_tunnel_token()
        token_encrypted = await self._encrypt_token(db, tunnel_token)

        try:
            db_pulse = await create_hpx_pulse(
                db,
                model=model,
                token_encrypted=token_encrypted,
                profile_id=meta["profile_id"],
                tunnel_mode=chosen.tunnel_mode,
                carrier=chosen.carrier,
                preset=chosen.preset,
                advice_json=advice.model_dump(mode="json"),
            )
            resolved_panel = await self._panel_url(panel_url)
            iran_t, iran_c, iran_c_alt, abroad_t, abroad_c, abroad_c_alt, exp = await self._issue_join_tokens(
                db, db_pulse, panel_url=resolved_panel
            )
            await db.commit()
        except IntegrityError:
            await db.rollback()
            await self.raise_error(message="Pulse name already exists", code=409)

        return HpxPulseActionResponse(
            pulse=_to_response(db_pulse),
            message="Pulse created — run join commands on Iran and abroad servers" + same_iran_warning,
            iran_join_token=iran_t,
            iran_join_command=iran_c,
            iran_join_command_alt=iran_c_alt,
            abroad_join_token=abroad_t,
            abroad_join_command=abroad_c,
            abroad_join_command_alt=abroad_c_alt,
            iran_join_expires_at=exp,
            abroad_join_expires_at=exp,
        )

    async def list_pulses(
        self,
        db: AsyncSession,
        *,
        admin: AdminDetails,
        offset: int = 0,
        limit: int = 50,
        name: str | None = None,
    ) -> HpxPulsesResponse:
        _ = admin
        rows, total = await get_hpx_pulses(db, offset=offset, limit=limit, name=name)
        return HpxPulsesResponse(pulses=[_to_response(r) for r in rows], total=total)

    async def get_pulse(self, db: AsyncSession, *, admin: AdminDetails, pulse_id: int) -> HpxPulseResponse:
        _ = admin
        db_pulse = await get_hpx_pulse_by_id(db, pulse_id)
        if db_pulse is None:
            await self.raise_error(message="Pulse not found", code=404)
        return _to_response(db_pulse)

    async def delete_pulse(self, db: AsyncSession, *, admin: AdminDetails, pulse_id: int) -> HpxPulseActionResponse:
        _ = admin
        db_pulse = await get_hpx_pulse_by_id(db, pulse_id)
        if db_pulse is None:
            await self.raise_error(message="Pulse not found", code=404)
        resp = _to_response(db_pulse)
        # Signal agents to uninstall before keys are removed (sync/ping runs every few seconds).
        await update_hpx_pulse(
            db,
            db_pulse,
            {
                "iran_agent_command": "leave",
                "abroad_agent_command": "leave",
                "status": HpxPulseStatus.stopped,
                "message": "Pulse deleted from panel — agents will uninstall",
            },
        )
        await db.commit()
        db_pulse = await get_hpx_pulse_by_id(db, pulse_id)
        if db_pulse is not None:
            await delete_hpx_pulse(db, db_pulse)
            await db.commit()
        return HpxPulseActionResponse(pulse=resp, message="Pulse deleted from panel")

    async def regenerate_tokens(
        self, db: AsyncSession, *, admin: AdminDetails, pulse_id: int, panel_url: str | None
    ) -> HpxPulseActionResponse:
        _ = admin
        db_pulse = await get_hpx_pulse_by_id(db, pulse_id)
        if db_pulse is None:
            await self.raise_error(message="Pulse not found", code=404)
        resolved_panel = await self._panel_url(panel_url)
        iran_t, iran_c, iran_c_alt, abroad_t, abroad_c, abroad_c_alt, exp = await self._issue_join_tokens(
            db, db_pulse, panel_url=resolved_panel
        )
        await db.commit()
        return HpxPulseActionResponse(
            pulse=_to_response(db_pulse),
            iran_join_token=iran_t,
            iran_join_command=iran_c,
            iran_join_command_alt=iran_c_alt,
            abroad_join_token=abroad_t,
            abroad_join_command=abroad_c,
            abroad_join_command_alt=abroad_c_alt,
            iran_join_expires_at=exp,
            abroad_join_expires_at=exp,
            message="Join tokens regenerated",
        )

    async def sync_pulse(self, db: AsyncSession, *, admin: AdminDetails, pulse_id: int) -> HpxPulseActionResponse:
        _ = admin
        db_pulse = await get_hpx_pulse_by_id(db, pulse_id)
        if db_pulse is None:
            await self.raise_error(message="Pulse not found", code=404)
        if not db_pulse.iran_agent_key_hash and not db_pulse.abroad_agent_key_hash:
            await self.raise_error(message="No agents connected — run join commands first", code=400)

        update: dict = {
            "message": "Sync requested — agents will refresh tunnel config",
            "last_status_change": dt.now(UTC),
        }
        if db_pulse.iran_agent_key_hash:
            update["iran_agent_command"] = "restart"
        if db_pulse.abroad_agent_key_hash:
            update["abroad_agent_command"] = "restart"
        db_pulse = await update_hpx_pulse(db, db_pulse, update)
        await db.commit()
        return HpxPulseActionResponse(
            pulse=_to_response(db_pulse),
            message="Sync queued for connected agents",
        )

    async def diagnose_pulse(self, db: AsyncSession, *, admin: AdminDetails, pulse_id: int) -> HpxPulseDiagnoseResponse:
        """TCP-reverse super agent: scan Hosts, force Extreme MSS, Sync+probe both sides."""
        _ = admin
        db_pulse = await get_hpx_pulse_by_id(db, pulse_id)
        if db_pulse is None:
            await self.raise_error(message="Pulse not found", code=404)

        fix_notes: list[str] = []
        hosts = await get_hosts(db)
        hits = scan_hosts_for_pulse(
            hosts,
            iran_ip=db_pulse.iran_public_ip,
            abroad_ip=db_pulse.abroad_public_ip,
        )
        rewritten: list = []
        iran_ip = (db_pulse.iran_public_ip or "").strip()
        abroad_ip = (db_pulse.abroad_public_ip or "").strip()
        if iran_ip and abroad_ip:
            for hit in hits:
                if hit.issue not in {"abroad_ip", "mixed"}:
                    continue
                db_host = next((h for h in hosts if getattr(h, "id", None) == hit.host_id), None)
                if db_host is None:
                    continue
                new_addrs = rewrite_host_addresses_to_iran(db_host.address, abroad_ip=abroad_ip, iran_ip=iran_ip)
                if new_addrs and new_addrs != set(db_host.address or set()):
                    db_host.address = new_addrs
                    rewritten.append(db_host)
                    fix_notes.append(f"Host #{hit.host_id} «{hit.remark}» address → Iran {iran_ip}")
            if rewritten:
                await db.flush()
                try:
                    await host_manager.add_hosts(db, rewritten)
                except Exception as exc:
                    logger.warning("host_manager refresh after Pulse diagnose autofix failed: %s", exc)

        # Re-scan after rewrite for diagnose rows.
        hosts = await get_hosts(db)
        hits = scan_hosts_for_pulse(
            hosts,
            iran_ip=db_pulse.iran_public_ip,
            abroad_ip=db_pulse.abroad_public_ip,
        )

        update: dict = {"last_health_check": dt.now(UTC)}
        extreme_id = should_autofix_tcp_extreme(db_pulse)
        if extreme_id:
            update.update(extreme_profile_update(extreme_id))
            fix_notes.append(f"profile → {extreme_id} (TCP Extreme mss=1000)")

        # Queue diagnose: agent applies latest TOML (hash change) then autofix+probes.
        probe_queued = False
        if db_pulse.iran_agent_key_hash:
            update["iran_agent_command"] = "diagnose"
            probe_queued = True
        if db_pulse.abroad_agent_key_hash:
            update["abroad_agent_command"] = "diagnose"
            probe_queued = True
        if fix_notes:
            update["message"] = "TCP autofix: " + "; ".join(fix_notes[:4])
            update["last_status_change"] = dt.now(UTC)

        db_pulse = await update_hpx_pulse(db, db_pulse, update)
        await db.commit()

        checks = diagnose_pulse_record(db_pulse)
        checks.extend(checks_from_linked_hosts(hits))
        if fix_notes:
            checks.insert(
                0,
                PulseDiagCheck(
                    f"Pulse: {db_pulse.name}",
                    "Autofix applied",
                    "info",
                    "; ".join(fix_notes),
                    "Agents Sync new TOML + deep TCP probes on next poll (~5–15s)",
                ),
            )
        summary = diagnose_summary(checks)

        hint = None
        if probe_queued:
            hint = (
                "TCP-reverse agent: Host rewrite + TCP Extreme (if needed) + Sync + "
                "firewall/TCPMSS/orphan/Xray autofix + TLS-via-Iran probe queued. "
                "Wait ~20s then Diagnose again for the fresh report"
            )
        elif fix_notes:
            hint = "Panel autofix applied (no agents joined yet — Tokens → join Iran & abroad)"
        return HpxPulseDiagnoseResponse(
            pulse_id=db_pulse.id,
            name=db_pulse.name,
            engine_pin=engine_version(),
            diag_report=db_pulse.diag_report if isinstance(db_pulse.diag_report, dict) else None,
            probe_queued=probe_queued,
            hint=hint,
            **summary,
        )

    async def path_ping(
        self,
        db: AsyncSession,
        *,
        admin: AdminDetails,
        pulse_id: int,
        model: HpxPulsePathPingRequest,
    ) -> HpxPulsePathPingResponse:
        """Queue abroad→Iran TCP/UDP multi-sample path ping (agent runs, panel polls path_ping)."""
        _ = admin
        db_pulse = await get_hpx_pulse_by_id(db, pulse_id)
        if db_pulse is None:
            await self.raise_error(message="Pulse not found", code=404)

        port: int | None = db_pulse.control_port
        if model.target == "forward":
            forwards = db_pulse.port_forwards or []
            if forwards:
                left = str(forwards[0]).split("=", 1)[0].strip()
                port = int(left) if left.isdigit() else port
            else:
                port = 443

        cmd = f"path-ping:{model.proto}:{model.count}:{model.target}"
        existing = db_pulse.diag_report if isinstance(db_pulse.diag_report, dict) else {}
        pending = {
            "status": "queued",
            "proto": model.proto,
            "count": model.count,
            "target": model.target,
            "port": port,
            "from": "abroad",
            "to": db_pulse.iran_public_ip,
            "ts": int(dt.now(UTC).timestamp()),
            "replies": [],
        }
        update: dict = {
            "last_health_check": dt.now(UTC),
            "diag_report": {**existing, "path_ping": pending},
            "message": f"Path ping queued ({model.proto.upper()} ×{model.count} → Iran {model.target})",
        }
        queued = False
        if db_pulse.abroad_agent_key_hash:
            update["abroad_agent_command"] = cmd
            queued = True
        elif db_pulse.iran_agent_key_hash:
            # Fallback: Iran probes itself (less useful) — prefer abroad.
            update["iran_agent_command"] = cmd
            pending["from"] = "iran"
            update["diag_report"] = {**existing, "path_ping": pending}
            queued = True

        db_pulse = await update_hpx_pulse(db, db_pulse, update)
        await db.commit()
        hint = None
        if queued:
            hint = "Abroad agent will sample Iran path in ~5–15s — keep this panel open"
        else:
            hint = "No agents joined — Tokens → join abroad (preferred) then Path Ping again"
        return HpxPulsePathPingResponse(
            pulse_id=db_pulse.id,
            name=db_pulse.name,
            queued=queued,
            proto=model.proto,
            count=model.count,
            target=model.target,
            port=port,
            hint=hint,
            path_ping=pending if queued else None,
        )

    async def update_pulse(
        self, db: AsyncSession, *, admin: AdminDetails, pulse_id: int, model: HpxPulseUpdate
    ) -> HpxPulseActionResponse:
        _ = admin
        db_pulse = await get_hpx_pulse_by_id(db, pulse_id)
        if db_pulse is None:
            await self.raise_error(message="Pulse not found", code=404)

        if model.name and model.name != db_pulse.name:
            duplicates, _ = await get_hpx_pulses(db, offset=0, limit=1, name=model.name)
            if any(item.id != db_pulse.id for item in duplicates):
                await self.raise_error(message="Pulse name already exists", code=409)

        update_data = model.model_dump(exclude_unset=True)
        if not update_data:
            await self.raise_error(message="No fields to update", code=422)

        if "auto_restart_interval_minutes" in update_data:
            interval = update_data["auto_restart_interval_minutes"]
            update_data["auto_restart_interval_minutes"] = interval if interval and interval > 0 else None

        if model.profile_id is not None:
            meta = profile_meta(model.profile_id)
            update_data["profile_id"] = meta["profile_id"]
            update_data["tunnel_mode"] = meta["tunnel_mode"]
            update_data["carrier"] = meta.get("carrier")
            update_data["preset"] = meta["preset"]

        if model.goal is not None:
            advise_req = PulseAdviseRequest(goal=model.goal, cpu_cores=1, ram_mb=1024)
            advice = advise(
                advise_req,
                domain=update_data.get("domain", db_pulse.domain),
                sni_hint=update_data.get("sni_hint", db_pulse.sni_hint),
                profile_override=update_data.get("profile_id", db_pulse.profile_id),
            )
            update_data["advice_json"] = advice.model_dump(mode="json")
            if model.profile_id is None:
                chosen = next(
                    (p for p in advice.profiles if p.profile_id == advice.recommended_profile_id), advice.profiles[0]
                )
                update_data["profile_id"] = chosen.profile_id
                update_data["tunnel_mode"] = chosen.tunnel_mode
                update_data["carrier"] = chosen.carrier
                update_data["preset"] = chosen.preset

        # Interval-only changes should not force an immediate agent restart.
        soft_keys = {
            "auto_restart_interval_minutes",
            "note",
            "enabled",
            "auto_heal_enabled",
            "backup_pulse_id",
            "auto_failover",
            "auto_failback",
            "priority",
        }
        needs_agent_restart = bool(set(update_data.keys()) - soft_keys)
        if needs_agent_restart:
            if db_pulse.iran_agent_key_hash:
                update_data.setdefault("iran_agent_command", "restart")
            if db_pulse.abroad_agent_key_hash:
                update_data.setdefault("abroad_agent_command", "restart")
            update_data.setdefault("message", "Config updated — agents syncing")
            update_data["last_status_change"] = dt.now(UTC)
        elif "auto_restart_interval_minutes" in update_data:
            interval = update_data["auto_restart_interval_minutes"]
            update_data.setdefault(
                "message",
                f"Auto-restart every {interval} min" if interval else "Auto-restart disabled",
            )

        db_pulse = await update_hpx_pulse(db, db_pulse, update_data)
        await db.commit()
        return HpxPulseActionResponse(pulse=_to_response(db_pulse), message="Pulse updated")

    async def claim_agent(
        self, db: AsyncSession, *, model: HpxPulseAgentClaimRequest, panel_url: str | None = None
    ) -> HpxPulseAgentBootstrap:
        side = model.side
        token_hash = hash_api_key(model.join_token)
        db_pulse = await get_hpx_pulse_by_join_token_hash(db, token_hash, side)
        if db_pulse is None:
            await self.raise_error(
                message="Invalid or unknown join token — regenerate tokens in the panel and paste the new command",
                code=401,
            )

        exp = db_pulse.iran_join_token_expires_at if side == "iran" else db_pulse.abroad_join_token_expires_at
        if exp and exp < dt.now(UTC):
            await self.raise_error(
                message="Join token expired — open the pulse in the panel and generate fresh join tokens",
                code=401,
            )

        agent_key = _mint_token("hpxpa" if side == "abroad" else "hpxpi")
        token = await self._decrypt_token(db, db_pulse)
        toml = render_for_side(side, db_pulse, token)
        cfg_hash = _config_hash(toml, side, db_pulse.id)

        update: dict = {
            "message": f"{side} agent claimed",
            "last_status_change": dt.now(UTC),
        }
        if side == "iran":
            update.update(
                {
                    "iran_join_token_hash": None,
                    "iran_join_token_expires_at": None,
                    "iran_agent_key_hash": hash_api_key(agent_key),
                    "iran_agent_claimed_at": dt.now(UTC),
                    "iran_agent_last_seen": dt.now(UTC),
                    "iran_agent_host": model.host,
                    "iran_agent_command": "start",
                }
            )
        else:
            update.update(
                {
                    "abroad_join_token_hash": None,
                    "abroad_join_token_expires_at": None,
                    "abroad_agent_key_hash": hash_api_key(agent_key),
                    "abroad_agent_claimed_at": dt.now(UTC),
                    "abroad_agent_last_seen": dt.now(UTC),
                    "abroad_agent_host": model.host,
                    "abroad_agent_command": "start",
                }
            )

        db_pulse = await update_hpx_pulse(db, db_pulse, update)
        both = bool(db_pulse.iran_agent_key_hash) and bool(db_pulse.abroad_agent_key_hash)
        if both:
            db_pulse = await update_hpx_pulse(
                db,
                db_pulse,
                {"status": HpxPulseStatus.starting, "message": "Both HPX agents connected — starting tunnel"},
            )
        else:
            db_pulse = await update_hpx_pulse(
                db,
                db_pulse,
                {"status": HpxPulseStatus.partial, "message": f"{side} HPX agent connected — waiting for other side"},
            )
        await db.commit()

        resolved_panel = await self._panel_url(panel_url)
        return HpxPulseAgentBootstrap(
            pulse_id=db_pulse.id,
            name=db_pulse.name,
            side=side,
            agent_key=agent_key,
            tunnel_toml=toml,
            config_hash=cfg_hash,
            control_port=db_pulse.control_port,
            abroad_public_ip=db_pulse.abroad_public_ip,
            iran_public_ip=db_pulse.iran_public_ip,
            tunnel_mode=db_pulse.tunnel_mode,
            port_forwards=db_pulse.port_forwards or [],
            agent_assets_base=agent_assets_base(resolved_panel),
        )

    async def _pulse_from_agent_key(self, db: AsyncSession, agent_key: str, side: str) -> HpxPulse:
        db_pulse = await get_hpx_pulse_by_agent_key_hash(db, hash_api_key(agent_key), side)
        if db_pulse is None:
            await self.raise_error(message="Invalid agent key", code=401)
        return db_pulse

    def _agent_config(self, db_pulse: HpxPulse, side: str, token: str) -> HpxPulseAgentConfigResponse:
        toml = render_for_side(side, db_pulse, token)
        return HpxPulseAgentConfigResponse(
            pulse_id=db_pulse.id,
            name=db_pulse.name,
            side=side,
            tunnel_toml=toml,
            config_hash=_config_hash(toml, side, db_pulse.id),
            desired_status=_desired_status(db_pulse),
            agent_command=db_pulse.iran_agent_command if side == "iran" else db_pulse.abroad_agent_command,
            enabled=db_pulse.enabled,
            tunnel_mode=db_pulse.tunnel_mode,
            control_port=db_pulse.control_port,
            iran_public_ip=db_pulse.iran_public_ip,
            abroad_public_ip=db_pulse.abroad_public_ip,
            port_forwards=db_pulse.port_forwards or [],
        )

    async def get_agent_config(self, db: AsyncSession, *, agent_key: str, side: str) -> HpxPulseAgentConfigResponse:
        db_pulse = await self._pulse_from_agent_key(db, agent_key, side)
        token = await self._decrypt_token(db, db_pulse)
        seen_key = "iran_agent_last_seen" if side == "iran" else "abroad_agent_last_seen"
        await update_hpx_pulse(db, db_pulse, {seen_key: dt.now(UTC)})
        await db.commit()
        return self._agent_config(db_pulse, side, token)

    async def agent_heartbeat(
        self, db: AsyncSession, *, agent_key: str, side: str, model: HpxPulseAgentHeartbeatRequest
    ) -> HpxPulseAgentConfigResponse:
        db_pulse = await self._pulse_from_agent_key(db, agent_key, side)
        token = await self._decrypt_token(db, db_pulse)
        prefix = "iran" if side == "iran" else "abroad"
        update_data = {
            f"{prefix}_agent_last_seen": dt.now(UTC),
            f"{prefix}_agent_host": model.host or getattr(db_pulse, f"{prefix}_agent_host"),
        }
        if model.message is not None:
            update_data["message"] = model.message
        # Only write latency when measured — null must not wipe a good reading from the other side.
        if model.latency_ms is not None:
            update_data["latency_ms"] = model.latency_ms
        if model.packet_loss_pct is not None:
            update_data["packet_loss_pct"] = model.packet_loss_pct
        if model.diag is not None:
            incoming = dict(model.diag)
            incoming.setdefault("side", side)
            existing = db_pulse.diag_report if isinstance(db_pulse.diag_report, dict) else {}
            sides = dict(existing.get("sides") or {})
            # Preserve flat legacy single-side reports under sides.<side>.
            if "sides" not in existing and existing.get("side"):
                sides[str(existing["side"])] = {k: v for k, v in existing.items() if k != "sides"}
            sides[side] = incoming
            merged = {
                "ts": incoming.get("ts"),
                "sides": sides,
            }
            # Preserve / refresh top-level path_ping from agent samples.
            path_ping = incoming.get("path_ping")
            if isinstance(path_ping, dict):
                merged["path_ping"] = path_ping
            elif isinstance(existing.get("path_ping"), dict):
                merged["path_ping"] = existing["path_ping"]
            update_data["diag_report"] = merged
            verdict = incoming.get("verdict") if isinstance(incoming.get("verdict"), dict) else None
            if verdict and verdict.get("summary") and model.message is None:
                update_data["message"] = str(verdict["summary"])[:240]
        if db_pulse.iran_agent_key_hash and db_pulse.abroad_agent_key_hash:
            if model.forward_ok is False:
                update_data["status"] = HpxPulseStatus.unhealthy
                update_data["message"] = model.message or (
                    "Tunnel control is up but forwarded port is not reachable — "
                    "open Iran firewall for 443 and ensure Xray listens on abroad 127.0.0.1:443"
                )
            elif model.status in {HpxPulseStatus.running.value, "running"} and (model.tunnel_running or model.iface_up):
                update_data["status"] = HpxPulseStatus.running
                if model.message is None and "message" not in update_data:
                    update_data["message"] = "HPX tunnel active"
            elif db_pulse.status in {HpxPulseStatus.starting, HpxPulseStatus.partial}:
                update_data["status"] = HpxPulseStatus.starting
                update_data["message"] = f"{side} agent online — waiting for tunnel link"
        db_pulse = await update_hpx_pulse(db, db_pulse, update_data)
        await db.commit()
        return self._agent_config(db_pulse, side, token)

    async def agent_ack(self, db: AsyncSession, *, agent_key: str, side: str, model: HpxPulseAgentAckRequest) -> None:
        db_pulse = await self._pulse_from_agent_key(db, agent_key, side)
        prefix = "iran" if side == "iran" else "abroad"
        await update_hpx_pulse(
            db,
            db_pulse,
            {
                f"{prefix}_agent_command": None,
                "message": model.message or f"{side} ack: {model.status}",
            },
        )
        await db.commit()
