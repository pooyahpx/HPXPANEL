import hashlib
import json
import secrets
from datetime import UTC, datetime as dt, timedelta as td

from sqlalchemy.exc import IntegrityError

from app.db import AsyncSession
from app.db.crud.general import get_jwt_secret_key
from app.db.crud.hpx_tunnel import (
    create_hpx_tunnel,
    delete_hpx_tunnel,
    get_hpx_tunnel_by_agent_key_hash,
    get_hpx_tunnel_by_id,
    get_hpx_tunnel_by_join_token_hash,
    get_hpx_tunnels,
    get_hpx_tunnels_by_ids,
    is_agent_managed,
    set_join_token,
    update_hpx_tunnel,
)
from app.db.models import HpxTunnel, HpxTunnelRole, HpxTunnelStatus
from app.models.admin import AdminDetails
from app.models.hpx_tunnel import (
    BulkHpxTunnelSelection,
    HpxPortForward,
    HpxTunnelActionResponse,
    HpxTunnelAgentAckRequest,
    HpxTunnelAgentBootstrap,
    HpxTunnelAgentClaimRequest,
    HpxTunnelAgentConfigResponse,
    HpxTunnelAgentHeartbeatRequest,
    HpxTunnelCreate,
    HpxTunnelJoinTokenResponse,
    HpxTunnelResponse,
    HpxTunnelsQuery,
    HpxTunnelsResponse,
    HpxTunnelStatsResponse,
    HpxTunnelUpdate,
    RemoveHpxTunnelsResponse,
)
from app.operation import BaseOperation
from app.services.hpx_tunnel.manager import (
    derive_status,
    get_container_logs,
    inspect_runtime,
    is_linux_host,
    ping_host,
    start_tunnel,
    stop_container,
)
from app.utils.crypto import decrypt_secret, encrypt_secret, hash_api_key
from app.utils.helpers import resolve_panel_base_url

JOIN_TOKEN_TTL_HOURS = 24
AGENT_SCRIPT_URL = "https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/scripts/hpx-tunnel-agent.sh"


def _to_response(db_tunnel: HpxTunnel) -> HpxTunnelResponse:
    data = HpxTunnelResponse.model_validate(db_tunnel).model_dump()
    data["has_password"] = bool(db_tunnel.password_encrypted)
    data["agent_claimed"] = bool(db_tunnel.agent_key_hash)
    # Never expose join token presence as usable after claim; expiry still useful while pending.
    if db_tunnel.agent_key_hash:
        data["join_token_expires_at"] = None
    return HpxTunnelResponse.model_validate(data)


def _mint_token(prefix: str = "hpx") -> str:
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def _build_join_command(panel_url: str | None, token: str) -> str:
    base = (panel_url or "https://YOUR_PANEL_HOST").rstrip("/")
    return (
        f'curl -fsSL {AGENT_SCRIPT_URL} | sudo bash -s -- join {token} --panel-url {base}'
    )


def _config_payload(db_tunnel: HpxTunnel, password: str) -> dict:
    port_forwards = db_tunnel.port_forwards or []
    return {
        "tunnel_id": db_tunnel.id,
        "name": db_tunnel.name,
        "role": db_tunnel.role.value if hasattr(db_tunnel.role, "value") else str(db_tunnel.role),
        "password": password,
        "remote_ip": db_tunnel.remote_ip,
        "interface": db_tunnel.interface,
        "local_ip": db_tunnel.local_ip,
        "subnet": db_tunnel.subnet,
        "mtu": db_tunnel.mtu,
        "keepalive": db_tunnel.keepalive,
        "dscp_mark": db_tunnel.dscp_mark,
        "port_forwards": port_forwards,
        "docker_image": db_tunnel.docker_image,
        "container_name": db_tunnel.container_name,
        "enabled": db_tunnel.enabled,
    }


def _config_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _desired_status(db_tunnel: HpxTunnel) -> HpxTunnelStatus:
    if not db_tunnel.enabled:
        return HpxTunnelStatus.stopped
    if db_tunnel.status == HpxTunnelStatus.pending_claim:
        return HpxTunnelStatus.running
    if db_tunnel.status in {HpxTunnelStatus.stopping, HpxTunnelStatus.stopped}:
        return HpxTunnelStatus.stopped
    return HpxTunnelStatus.running


class HpxTunnelOperation(BaseOperation):
    async def _secret_key(self, db: AsyncSession) -> str:
        return await get_jwt_secret_key(db)

    async def _decrypt_password(self, db: AsyncSession, db_tunnel: HpxTunnel) -> str:
        secret = await self._secret_key(db)
        return decrypt_secret(db_tunnel.password_encrypted, secret)

    async def _encrypt_password(self, db: AsyncSession, password: str) -> str:
        secret = await self._secret_key(db)
        return encrypt_secret(password, secret)

    async def _panel_url(self, request_base: str | None = None) -> str | None:
        resolved = await resolve_panel_base_url()
        if resolved:
            return resolved
        if request_base:
            return request_base.rstrip("/")
        return None

    async def _issue_join_token(
        self, db: AsyncSession, db_tunnel: HpxTunnel, *, panel_url: str | None
    ) -> tuple[str, str, dt]:
        token = _mint_token("hpx")
        expires_at = dt.now(UTC) + td(hours=JOIN_TOKEN_TTL_HOURS)
        set_join_token(db_tunnel, token=token, expires_at=expires_at)
        # Reset agent binding when regenerating so a new Iran host can claim.
        db_tunnel.agent_key_hash = None
        db_tunnel.agent_claimed_at = None
        db_tunnel.agent_last_seen = None
        db_tunnel.agent_host = None
        db_tunnel.agent_command = None
        db_tunnel.status = HpxTunnelStatus.pending_claim
        db_tunnel.message = "Waiting for Iran agent join"
        db_tunnel.last_status_change = dt.now(UTC)
        await db.flush()
        command = _build_join_command(panel_url, token)
        return token, command, expires_at

    def _agent_config_response(
        self, db_tunnel: HpxTunnel, password: str
    ) -> HpxTunnelAgentConfigResponse:
        payload = _config_payload(db_tunnel, password)
        return HpxTunnelAgentConfigResponse(
            tunnel_id=db_tunnel.id,
            name=db_tunnel.name,
            role=db_tunnel.role,
            password=password,
            remote_ip=db_tunnel.remote_ip,
            interface=db_tunnel.interface,
            local_ip=db_tunnel.local_ip,
            subnet=db_tunnel.subnet,
            mtu=db_tunnel.mtu,
            keepalive=db_tunnel.keepalive,
            dscp_mark=db_tunnel.dscp_mark,
            port_forwards=[HpxPortForward.model_validate(item) for item in (db_tunnel.port_forwards or [])],
            docker_image=db_tunnel.docker_image,
            container_name=db_tunnel.container_name,
            config_hash=_config_hash(payload),
            desired_status=_desired_status(db_tunnel),
            agent_command=db_tunnel.agent_command,
            enabled=db_tunnel.enabled,
        )

    async def _refresh_runtime(
        self,
        db: AsyncSession,
        db_tunnel: HpxTunnel,
        *,
        ping: bool = True,
    ) -> HpxTunnel:
        if is_agent_managed(db_tunnel) or db_tunnel.status == HpxTunnelStatus.pending_claim:
            if ping and db_tunnel.role == HpxTunnelRole.iran and db_tunnel.remote_ip:
                latency_ms, packet_loss_pct = await ping_host(db_tunnel.remote_ip)
                return await update_hpx_tunnel(
                    db,
                    db_tunnel,
                    {
                        "latency_ms": latency_ms,
                        "packet_loss_pct": packet_loss_pct,
                        "last_health_check": dt.now(UTC),
                    },
                )
            return db_tunnel

        runtime = await inspect_runtime(db_tunnel)
        latency_ms = db_tunnel.latency_ms
        packet_loss_pct = db_tunnel.packet_loss_pct

        if ping and db_tunnel.role == HpxTunnelRole.iran and db_tunnel.remote_ip:
            latency_ms, packet_loss_pct = await ping_host(db_tunnel.remote_ip)

        new_status = derive_status(db_tunnel, runtime, latency_ms, packet_loss_pct)
        previous_status = db_tunnel.status
        update_data = {
            "status": new_status,
            "latency_ms": latency_ms,
            "packet_loss_pct": packet_loss_pct,
            "bytes_up": runtime.bytes_up,
            "bytes_down": runtime.bytes_down,
            "last_health_check": dt.now(UTC),
            "message": runtime.message,
        }
        if previous_status != new_status:
            update_data["last_status_change"] = dt.now(UTC)
        return await update_hpx_tunnel(db, db_tunnel, update_data)

    async def create_tunnel(
        self,
        db: AsyncSession,
        *,
        admin: AdminDetails,
        model: HpxTunnelCreate,
        panel_url: str | None = None,
    ) -> HpxTunnelActionResponse:
        if model.role == HpxTunnelRole.foreign and not is_linux_host():
            await self.raise_error(
                message="FOREIGN HPX tunnels require a Linux panel host with Docker",
                code=422,
            )

        duplicates, _ = await get_hpx_tunnels(db, offset=0, limit=1, name=model.name)
        if duplicates:
            await self.raise_error(message="Tunnel name already exists", code=409)

        if model.backup_tunnel_id is not None:
            backup = await get_hpx_tunnel_by_id(db, model.backup_tunnel_id)
            if backup is None:
                await self.raise_error(message="Backup tunnel not found", code=404)

        try:
            encrypted = await self._encrypt_password(db, model.password)
            db_tunnel = await create_hpx_tunnel(db, model=model, password_encrypted=encrypted)
            await db.commit()
        except IntegrityError:
            await self.raise_error(message="Tunnel already exists", code=409, db=db)

        join_token = None
        join_command = None
        join_expires_at = None
        message = None

        if model.role == HpxTunnelRole.iran:
            resolved_panel = await self._panel_url(panel_url)
            join_token, join_command, join_expires_at = await self._issue_join_token(
                db, db_tunnel, panel_url=resolved_panel
            )
            await db.commit()
            message = "Iran tunnel created. Run the join command on the Iran server."
        elif model.start_after_create:
            db_tunnel.status = HpxTunnelStatus.starting
            await db.commit()
            ok, err = await start_tunnel(db_tunnel, model.password)
            if ok:
                db_tunnel = await self._refresh_runtime(db, db_tunnel)
                message = "Tunnel started successfully"
            else:
                db_tunnel.status = HpxTunnelStatus.error
                db_tunnel.message = err
                message = err
            await db.commit()

        return HpxTunnelActionResponse(
            tunnel=_to_response(db_tunnel),
            message=message,
            join_token=join_token,
            join_command=join_command,
            join_expires_at=join_expires_at,
        )

    async def regenerate_join_token(
        self,
        db: AsyncSession,
        *,
        admin: AdminDetails,
        tunnel_id: int,
        panel_url: str | None = None,
    ) -> HpxTunnelJoinTokenResponse:
        db_tunnel = await get_hpx_tunnel_by_id(db, tunnel_id)
        if db_tunnel is None:
            await self.raise_error(message="Tunnel not found", code=404)
        if db_tunnel.role != HpxTunnelRole.iran:
            await self.raise_error(message="Join tokens are only for IRAN tunnels", code=422)

        resolved_panel = await self._panel_url(panel_url)
        token, command, expires_at = await self._issue_join_token(
            db, db_tunnel, panel_url=resolved_panel
        )
        await db.commit()
        return HpxTunnelJoinTokenResponse(
            tunnel_id=db_tunnel.id,
            join_token=token,
            join_command=command,
            join_expires_at=expires_at,
        )

    async def list_tunnels(
        self, db: AsyncSession, *, admin: AdminDetails, query: HpxTunnelsQuery
    ) -> HpxTunnelsResponse:
        offset = query.offset or 0
        limit = query.limit or 100
        rows, total = await get_hpx_tunnels(
            db,
            offset=offset,
            limit=limit,
            tunnel_id=query.tunnel_id,
            name=query.name,
            role=query.role,
            status=query.status,
        )
        return HpxTunnelsResponse(tunnels=[_to_response(row) for row in rows], total=total)

    async def get_tunnel(self, db: AsyncSession, *, admin: AdminDetails, tunnel_id: int) -> HpxTunnelResponse:
        db_tunnel = await get_hpx_tunnel_by_id(db, tunnel_id)
        if db_tunnel is None:
            await self.raise_error(message="Tunnel not found", code=404)
        return _to_response(db_tunnel)

    async def modify_tunnel(
        self, db: AsyncSession, *, admin: AdminDetails, tunnel_id: int, model: HpxTunnelUpdate
    ) -> HpxTunnelResponse:
        db_tunnel = await get_hpx_tunnel_by_id(db, tunnel_id)
        if db_tunnel is None:
            await self.raise_error(message="Tunnel not found", code=404)

        if model.name and model.name != db_tunnel.name:
            duplicates, _ = await get_hpx_tunnels(db, offset=0, limit=1, name=model.name)
            if any(item.id != db_tunnel.id for item in duplicates):
                await self.raise_error(message="Tunnel name already exists", code=409)

        if model.backup_tunnel_id is not None and model.backup_tunnel_id == db_tunnel.id:
            await self.raise_error(message="Tunnel cannot be its own backup", code=422)

        update_data = model.model_dump(exclude_unset=True)
        if model.password:
            update_data["password_encrypted"] = await self._encrypt_password(db, model.password)
        update_data.pop("password", None)
        if "port_forwards" in update_data and update_data["port_forwards"] is not None:
            update_data["port_forwards"] = [item.model_dump() for item in model.port_forwards or []]

        if is_agent_managed(db_tunnel) and update_data:
            update_data.setdefault("agent_command", "restart")
            update_data.setdefault("message", "Config updated — waiting for Iran agent sync")

        db_tunnel = await update_hpx_tunnel(db, db_tunnel, update_data)
        await db.commit()
        return _to_response(db_tunnel)

    async def delete_tunnel(self, db: AsyncSession, *, admin: AdminDetails, tunnel_id: int) -> None:
        db_tunnel = await get_hpx_tunnel_by_id(db, tunnel_id)
        if db_tunnel is None:
            await self.raise_error(message="Tunnel not found", code=404)

        if not is_agent_managed(db_tunnel):
            await stop_container(db_tunnel.container_name)
        await delete_hpx_tunnel(db, db_tunnel)
        await db.commit()

    async def bulk_delete_tunnels(
        self, db: AsyncSession, *, admin: AdminDetails, bulk: BulkHpxTunnelSelection
    ) -> RemoveHpxTunnelsResponse:
        db_tunnels = await get_hpx_tunnels_by_ids(db, bulk.ids)
        found_ids = {item.id for item in db_tunnels}
        for tunnel_id in bulk.ids:
            if tunnel_id not in found_ids:
                await self.raise_error(message="Tunnel not found", code=404)

        names: list[str] = []
        for db_tunnel in db_tunnels:
            names.append(db_tunnel.name)
            if not is_agent_managed(db_tunnel):
                await stop_container(db_tunnel.container_name)
            await delete_hpx_tunnel(db, db_tunnel)
        await db.commit()
        return RemoveHpxTunnelsResponse(tunnels=names, count=len(names))

    async def start_tunnel_action(
        self, db: AsyncSession, *, admin: AdminDetails, tunnel_id: int
    ) -> HpxTunnelActionResponse:
        db_tunnel = await get_hpx_tunnel_by_id(db, tunnel_id)
        if db_tunnel is None:
            await self.raise_error(message="Tunnel not found", code=404)

        if db_tunnel.role == HpxTunnelRole.iran and not is_agent_managed(db_tunnel):
            if db_tunnel.status == HpxTunnelStatus.pending_claim or db_tunnel.join_token_hash:
                return HpxTunnelActionResponse(
                    tunnel=_to_response(db_tunnel),
                    message="Run the join token on the Iran server first",
                )
            await self.raise_error(
                message="IRAN tunnels must be started via the Iran agent join token",
                code=422,
            )

        if is_agent_managed(db_tunnel):
            db_tunnel = await update_hpx_tunnel(
                db,
                db_tunnel,
                {
                    "enabled": True,
                    "status": HpxTunnelStatus.starting,
                    "agent_command": "start",
                    "message": "Start requested — waiting for Iran agent",
                    "last_status_change": dt.now(UTC),
                },
            )
            await db.commit()
            return HpxTunnelActionResponse(
                tunnel=_to_response(db_tunnel),
                message="Start queued for Iran agent",
            )

        password = await self._decrypt_password(db, db_tunnel)
        db_tunnel.status = HpxTunnelStatus.starting
        await db.commit()

        ok, err = await start_tunnel(db_tunnel, password)
        if not ok:
            db_tunnel.status = HpxTunnelStatus.error
            db_tunnel.message = err
            await db.commit()
            return HpxTunnelActionResponse(tunnel=_to_response(db_tunnel), message=err)

        db_tunnel = await self._refresh_runtime(db, db_tunnel)
        await db.commit()
        return HpxTunnelActionResponse(tunnel=_to_response(db_tunnel), message="Tunnel started")

    async def stop_tunnel_action(
        self, db: AsyncSession, *, admin: AdminDetails, tunnel_id: int
    ) -> HpxTunnelActionResponse:
        db_tunnel = await get_hpx_tunnel_by_id(db, tunnel_id)
        if db_tunnel is None:
            await self.raise_error(message="Tunnel not found", code=404)

        if is_agent_managed(db_tunnel):
            db_tunnel = await update_hpx_tunnel(
                db,
                db_tunnel,
                {
                    "status": HpxTunnelStatus.stopping,
                    "agent_command": "stop",
                    "message": "Stop requested — waiting for Iran agent",
                    "last_status_change": dt.now(UTC),
                },
            )
            await db.commit()
            return HpxTunnelActionResponse(
                tunnel=_to_response(db_tunnel),
                message="Stop queued for Iran agent",
            )

        db_tunnel.status = HpxTunnelStatus.stopping
        await db.commit()
        ok, err = await stop_container(db_tunnel.container_name)
        db_tunnel.status = HpxTunnelStatus.stopped if ok else HpxTunnelStatus.error
        db_tunnel.message = err
        db_tunnel.last_status_change = dt.now(UTC)
        await db.commit()
        return HpxTunnelActionResponse(tunnel=_to_response(db_tunnel), message=err)

    async def restart_tunnel_action(
        self, db: AsyncSession, *, admin: AdminDetails, tunnel_id: int
    ) -> HpxTunnelActionResponse:
        db_tunnel = await get_hpx_tunnel_by_id(db, tunnel_id)
        if db_tunnel is None:
            await self.raise_error(message="Tunnel not found", code=404)

        if is_agent_managed(db_tunnel):
            db_tunnel = await update_hpx_tunnel(
                db,
                db_tunnel,
                {
                    "enabled": True,
                    "status": HpxTunnelStatus.starting,
                    "agent_command": "restart",
                    "message": "Restart requested — waiting for Iran agent",
                    "last_status_change": dt.now(UTC),
                },
            )
            await db.commit()
            return HpxTunnelActionResponse(
                tunnel=_to_response(db_tunnel),
                message="Restart queued for Iran agent",
            )

        await self.stop_tunnel_action(db, admin=admin, tunnel_id=tunnel_id)
        return await self.start_tunnel_action(db, admin=admin, tunnel_id=tunnel_id)

    async def get_tunnel_stats(
        self, db: AsyncSession, *, admin: AdminDetails, tunnel_id: int
    ) -> HpxTunnelStatsResponse:
        db_tunnel = await get_hpx_tunnel_by_id(db, tunnel_id)
        if db_tunnel is None:
            await self.raise_error(message="Tunnel not found", code=404)

        db_tunnel = await self._refresh_runtime(db, db_tunnel)
        await db.commit()

        if is_agent_managed(db_tunnel) or db_tunnel.status == HpxTunnelStatus.pending_claim:
            return HpxTunnelStatsResponse(
                tunnel_id=db_tunnel.id,
                status=db_tunnel.status,
                container_running=db_tunnel.status == HpxTunnelStatus.running,
                interface_up=db_tunnel.status == HpxTunnelStatus.running,
                interface_ip=db_tunnel.local_ip if db_tunnel.status == HpxTunnelStatus.running else None,
                latency_ms=db_tunnel.latency_ms,
                packet_loss_pct=db_tunnel.packet_loss_pct,
                bytes_up=db_tunnel.bytes_up,
                bytes_down=db_tunnel.bytes_down,
                uptime_seconds=None,
                message=db_tunnel.message,
            )

        runtime = await inspect_runtime(db_tunnel)
        return HpxTunnelStatsResponse(
            tunnel_id=db_tunnel.id,
            status=db_tunnel.status,
            container_running=runtime.container_running,
            interface_up=runtime.interface_up,
            interface_ip=runtime.interface_ip,
            latency_ms=db_tunnel.latency_ms,
            packet_loss_pct=db_tunnel.packet_loss_pct,
            bytes_up=db_tunnel.bytes_up,
            bytes_down=db_tunnel.bytes_down,
            uptime_seconds=runtime.uptime_seconds,
            message=db_tunnel.message,
        )

    async def get_tunnel_logs(self, db: AsyncSession, *, admin: AdminDetails, tunnel_id: int) -> str:
        db_tunnel = await get_hpx_tunnel_by_id(db, tunnel_id)
        if db_tunnel is None:
            await self.raise_error(message="Tunnel not found", code=404)
        if is_agent_managed(db_tunnel) or db_tunnel.status == HpxTunnelStatus.pending_claim:
            host = db_tunnel.agent_host or "Iran agent"
            last_seen = db_tunnel.agent_last_seen.isoformat() if db_tunnel.agent_last_seen else "never"
            return (
                f"IRAN tunnel is agent-managed on {host}.\n"
                f"Last seen: {last_seen}\n"
                f"Status: {db_tunnel.status}\n"
                f"Message: {db_tunnel.message or '-'}\n"
                "Use `hpx-tunnel-agent logs` on the Iran server for container logs."
            )
        return await get_container_logs(db_tunnel.container_name)

    async def claim_agent(
        self, db: AsyncSession, *, model: HpxTunnelAgentClaimRequest
    ) -> HpxTunnelAgentBootstrap:
        token_hash = hash_api_key(model.join_token)
        db_tunnel = await get_hpx_tunnel_by_join_token_hash(db, token_hash)
        if db_tunnel is None:
            await self.raise_error(message="Invalid join token", code=401)
        if db_tunnel.role != HpxTunnelRole.iran:
            await self.raise_error(message="Join token is not for an IRAN tunnel", code=422)
        if db_tunnel.join_token_expires_at and db_tunnel.join_token_expires_at < dt.now(UTC):
            await self.raise_error(message="Join token expired", code=401)

        agent_key = _mint_token("hpxa")
        password = await self._decrypt_password(db, db_tunnel)
        db_tunnel = await update_hpx_tunnel(
            db,
            db_tunnel,
            {
                "join_token_hash": None,
                "join_token_expires_at": None,
                "agent_key_hash": hash_api_key(agent_key),
                "agent_claimed_at": dt.now(UTC),
                "agent_last_seen": dt.now(UTC),
                "agent_host": model.host,
                "agent_command": "start",
                "status": HpxTunnelStatus.starting,
                "message": "Claimed by Iran agent",
                "last_status_change": dt.now(UTC),
            },
        )
        await db.commit()

        cfg = self._agent_config_response(db_tunnel, password)
        return HpxTunnelAgentBootstrap(
            **cfg.model_dump(exclude={"enabled"}),
            agent_key=agent_key,
        )

    async def _tunnel_from_agent_key(self, db: AsyncSession, agent_key: str) -> HpxTunnel:
        db_tunnel = await get_hpx_tunnel_by_agent_key_hash(db, hash_api_key(agent_key))
        if db_tunnel is None:
            await self.raise_error(message="Invalid agent key", code=401)
        return db_tunnel

    async def get_agent_config(self, db: AsyncSession, *, agent_key: str) -> HpxTunnelAgentConfigResponse:
        db_tunnel = await self._tunnel_from_agent_key(db, agent_key)
        password = await self._decrypt_password(db, db_tunnel)
        db_tunnel = await update_hpx_tunnel(db, db_tunnel, {"agent_last_seen": dt.now(UTC)})
        await db.commit()
        return self._agent_config_response(db_tunnel, password)

    async def agent_heartbeat(
        self, db: AsyncSession, *, agent_key: str, model: HpxTunnelAgentHeartbeatRequest
    ) -> HpxTunnelAgentConfigResponse:
        db_tunnel = await self._tunnel_from_agent_key(db, agent_key)
        update_data = {
            "status": model.status,
            "agent_last_seen": dt.now(UTC),
            "agent_host": model.host or db_tunnel.agent_host,
            "latency_ms": model.latency_ms,
            "packet_loss_pct": model.packet_loss_pct,
            "bytes_up": model.bytes_up,
            "bytes_down": model.bytes_down,
            "message": model.message,
            "last_health_check": dt.now(UTC),
        }
        if model.status != db_tunnel.status:
            update_data["last_status_change"] = dt.now(UTC)
        db_tunnel = await update_hpx_tunnel(db, db_tunnel, update_data)
        await db.commit()
        password = await self._decrypt_password(db, db_tunnel)
        return self._agent_config_response(db_tunnel, password)

    async def agent_ack(
        self, db: AsyncSession, *, agent_key: str, model: HpxTunnelAgentAckRequest
    ) -> HpxTunnelAgentConfigResponse:
        db_tunnel = await self._tunnel_from_agent_key(db, agent_key)
        update_data: dict = {
            "agent_last_seen": dt.now(UTC),
            "agent_command": None,
        }
        if model.status is not None:
            update_data["status"] = model.status
            update_data["last_status_change"] = dt.now(UTC)
        if model.message is not None:
            update_data["message"] = model.message
        db_tunnel = await update_hpx_tunnel(db, db_tunnel, update_data)
        await db.commit()
        password = await self._decrypt_password(db, db_tunnel)
        return self._agent_config_response(db_tunnel, password)
