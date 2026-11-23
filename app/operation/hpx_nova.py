from __future__ import annotations

import secrets
from datetime import UTC, datetime as dt, timedelta as td

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud.hpx_nova import (
    create_hpx_nova,
    delete_hpx_nova,
    get_hpx_nova_by_agent_key_hash,
    get_hpx_nova_by_id,
    get_hpx_nova_by_join_token_hash,
    get_hpx_novas,
    set_join_token,
    update_hpx_nova,
)
from app.db.crud.general import get_jwt_secret_key
from app.db.models import HpxNova, HpxNovaStatus
from app.models.admin import AdminDetails
from app.models.hpx_nova import (
    HpxNovaActionResponse,
    HpxNovaAgentAckRequest,
    HpxNovaAgentBootstrap,
    HpxNovaAgentClaimRequest,
    HpxNovaAgentConfigResponse,
    HpxNovaAgentHeartbeatRequest,
    HpxNovaCreate,
    HpxNovaResponse,
    HpxNovasResponse,
    HpxNovaUpdate,
)
from app.operation import BaseOperation, OperatorType
from app.services.hpx_nova import engine_mirror
from app.services.hpx_nova.config_render import normalize_port_forwards, render_nova_config
from app.services.hpx_nova.identity import identity_from_json, identity_to_json, mint_nova_identity
from app.utils.crypto import decrypt_secret, encrypt_secret, hash_api_key
from app.utils.logger import get_logger
logger = get_logger("hpx-nova")

JOIN_TOKEN_TTL_HOURS = 24
AGENT_ONLINE_SECONDS = 180


def _mint_token(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(24)}"


def _build_join_command_panel(panel_url: str | None, token: str, side: str) -> str:
    base = (panel_url or "https://YOUR_PANEL_HOST").rstrip("/")
    return (
        f"curl --http1.1 -fsSL {base}/api/hpx_nova/agent/hpx-nova-agent.sh | "
        f"sudo env PANEL_URL={base} JOIN_TOKEN={token} SIDE={side} bash"
    )


def _build_join_command_github(panel_url: str | None, token: str, side: str) -> str:
    repo = "pooyahpx/HPXPANEL"
    base = (panel_url or "https://YOUR_PANEL_HOST").rstrip("/")
    return (
        f"curl --http1.1 -fsSL https://raw.githubusercontent.com/{repo}/main/scripts/hpx-nova-agent.sh | "
        f"sudo env PANEL_URL={base} JOIN_TOKEN={token} SIDE={side} bash"
    )


class HpxNovaOperation(BaseOperation):
    def __init__(self, operator_type: OperatorType = OperatorType.API):
        super().__init__(operator_type)

    async def _encrypt_identity(self, db: AsyncSession, identity: dict) -> str:
        return encrypt_secret(identity_to_json(identity), await get_jwt_secret_key(db))

    async def _decrypt_identity(self, db: AsyncSession, row: HpxNova) -> dict[str, str]:
        return identity_from_json(decrypt_secret(row.identity_encrypted, await get_jwt_secret_key(db)))

    def _online(self, seen: dt | None) -> bool:
        if not seen:
            return False
        if seen.tzinfo is None:
            seen = seen.replace(tzinfo=UTC)
        return (dt.now(UTC) - seen).total_seconds() <= AGENT_ONLINE_SECONDS

    def _to_response(self, row: HpxNova) -> HpxNovaResponse:
        return HpxNovaResponse(
            id=row.id,
            name=row.name,
            status=HpxNovaStatus(row.status) if not isinstance(row.status, HpxNovaStatus) else row.status,
            enabled=bool(row.enabled),
            engine=row.engine or "nova",
            carrier=row.carrier or "wss",
            lanes=int(row.lanes or 4),
            resume=bool(row.resume),
            iran_public_ip=row.iran_public_ip,
            abroad_public_ip=row.abroad_public_ip,
            tunnel_port=int(row.tunnel_port or 8443),
            sni=row.sni,
            ws_path=row.ws_path,
            port_forwards=list(row.port_forwards or []),
            proxy_listen=row.proxy_listen,
            note=row.note,
            iran_claimed=bool(row.iran_agent_key_hash),
            abroad_claimed=bool(row.abroad_agent_key_hash),
            iran_agent_online=self._online(row.iran_agent_last_seen),
            abroad_agent_online=self._online(row.abroad_agent_last_seen),
            iran_agent_host=row.iran_agent_host,
            abroad_agent_host=row.abroad_agent_host,
            iran_agent_last_seen=row.iran_agent_last_seen,
            abroad_agent_last_seen=row.abroad_agent_last_seen,
            latency_ms=row.latency_ms,
            message=row.message,
            created_at=row.created_at,
            last_status_change=row.last_status_change,
        )

    async def _issue_join_tokens(
        self, db: AsyncSession, row: HpxNova, *, panel_url: str | None
    ) -> tuple[str, str, str, str, str, str, dt]:
        expires_at = dt.now(UTC) + td(hours=JOIN_TOKEN_TTL_HOURS)
        iran_token = _mint_token("hpxni")
        abroad_token = _mint_token("hpxna")
        set_join_token(row, side="iran", token=iran_token, expires_at=expires_at)
        set_join_token(row, side="abroad", token=abroad_token, expires_at=expires_at)
        await db.commit()
        await db.refresh(row)
        iran_cmd = _build_join_command_panel(panel_url, iran_token, "iran")
        iran_alt = _build_join_command_github(panel_url, iran_token, "iran")
        abroad_cmd = _build_join_command_panel(panel_url, abroad_token, "abroad")
        abroad_alt = _build_join_command_github(panel_url, abroad_token, "abroad")
        return iran_token, iran_cmd, iran_alt, abroad_token, abroad_cmd, abroad_alt, expires_at

    def _render(self, row: HpxNova, identity: dict[str, str], side: str) -> str:
        return render_nova_config(
            side=side,
            identity=identity,
            carrier=row.carrier or "wss",
            lanes=int(row.lanes or 4),
            resume=bool(row.resume),
            tunnel_port=int(row.tunnel_port or 8443),
            iran_public_ip=row.iran_public_ip,
            sni=row.sni,
            ws_path=row.ws_path,
            port_forwards=list(row.port_forwards or []),
            proxy_listen=row.proxy_listen,
            nova_id=int(row.id),
        )

    async def create_nova(
        self,
        db: AsyncSession,
        *,
        admin: AdminDetails,
        model: HpxNovaCreate,
        panel_url: str | None = None,
    ) -> HpxNovaActionResponse:
        _ = admin
        existing, _ = await get_hpx_novas(db, offset=0, limit=1, name=model.name)
        if existing:
            await self.raise_error(message="Nova name already exists", code=409)

        identity = mint_nova_identity()
        row = await create_hpx_nova(
            db,
            name=model.name,
            identity_encrypted=await self._encrypt_identity(db, identity),
            iran_public_ip=model.iran_public_ip.strip(),
            abroad_public_ip=model.abroad_public_ip.strip(),
            carrier=model.carrier.value if hasattr(model.carrier, "value") else str(model.carrier),
            lanes=model.lanes,
            resume=model.resume,
            tunnel_port=model.tunnel_port,
            sni=model.sni,
            ws_path=model.ws_path,
            port_forwards=normalize_port_forwards(model.port_forwards),
            proxy_listen=model.proxy_listen,
            note=model.note,
        )
        iran_token, iran_cmd, iran_alt, abroad_token, abroad_cmd, abroad_alt, expires = await self._issue_join_tokens(
            db, row, panel_url=panel_url
        )
        return HpxNovaActionResponse(
            detail="HPX Nova tunnel created",
            nova=self._to_response(row),
            iran_join_token=iran_token,
            abroad_join_token=abroad_token,
            iran_join_command=iran_cmd,
            iran_join_command_alt=iran_alt,
            abroad_join_command=abroad_cmd,
            abroad_join_command_alt=abroad_alt,
            join_expires_at=expires,
        )

    async def list_novas(
        self,
        db: AsyncSession,
        *,
        admin: AdminDetails,
        offset: int = 0,
        limit: int = 50,
        name: str | None = None,
    ) -> HpxNovasResponse:
        _ = admin
        rows, total = await get_hpx_novas(db, offset=offset, limit=limit, name=name)
        return HpxNovasResponse(novas=[self._to_response(r) for r in rows], total=total)

    async def get_nova(self, db: AsyncSession, *, admin: AdminDetails, nova_id: int) -> HpxNovaResponse:
        _ = admin
        row = await get_hpx_nova_by_id(db, nova_id)
        if row is None:
            await self.raise_error(message="Nova not found", code=404)
        return self._to_response(row)

    async def update_nova(
        self,
        db: AsyncSession,
        *,
        admin: AdminDetails,
        nova_id: int,
        model: HpxNovaUpdate,
    ) -> HpxNovaActionResponse:
        _ = admin
        row = await get_hpx_nova_by_id(db, nova_id)
        if row is None:
            await self.raise_error(message="Nova not found", code=404)
        fields = model.model_dump(exclude_none=True)
        if "port_forwards" in fields:
            fields["port_forwards"] = normalize_port_forwards(fields["port_forwards"])
        if fields:
            if row.iran_agent_key_hash:
                fields.setdefault("iran_agent_command", "restart")
            if row.abroad_agent_key_hash:
                fields.setdefault("abroad_agent_command", "restart")
            row = await update_hpx_nova(db, row, fields)
        return HpxNovaActionResponse(detail="Nova updated", nova=self._to_response(row))

    async def delete_nova(self, db: AsyncSession, *, admin: AdminDetails, nova_id: int) -> HpxNovaActionResponse:
        _ = admin
        row = await get_hpx_nova_by_id(db, nova_id)
        if row is None:
            await self.raise_error(message="Nova not found", code=404)
        await delete_hpx_nova(db, row)
        return HpxNovaActionResponse(detail="Nova deleted")

    async def regenerate_join(
        self, db: AsyncSession, *, admin: AdminDetails, nova_id: int, panel_url: str | None
    ) -> HpxNovaActionResponse:
        _ = admin
        row = await get_hpx_nova_by_id(db, nova_id)
        if row is None:
            await self.raise_error(message="Nova not found", code=404)
        fields = {
            "status": HpxNovaStatus.pending_claim,
            "message": "Join tokens regenerated",
            "last_status_change": dt.now(UTC),
            "iran_agent_key_hash": None,
            "abroad_agent_key_hash": None,
            "iran_agent_claimed_at": None,
            "abroad_agent_claimed_at": None,
            "iran_agent_command": "leave",
            "abroad_agent_command": "leave",
        }
        row = await update_hpx_nova(db, row, fields)
        iran_token, iran_cmd, iran_alt, abroad_token, abroad_cmd, abroad_alt, expires = await self._issue_join_tokens(
            db, row, panel_url=panel_url
        )
        return HpxNovaActionResponse(
            detail="Nova join tokens regenerated",
            nova=self._to_response(row),
            iran_join_token=iran_token,
            abroad_join_token=abroad_token,
            iran_join_command=iran_cmd,
            iran_join_command_alt=iran_alt,
            abroad_join_command=abroad_cmd,
            abroad_join_command_alt=abroad_alt,
            join_expires_at=expires,
        )

    async def sync_nova(self, db: AsyncSession, *, admin: AdminDetails, nova_id: int) -> HpxNovaActionResponse:
        _ = admin
        row = await get_hpx_nova_by_id(db, nova_id)
        if row is None:
            await self.raise_error(message="Nova not found", code=404)
        fields: dict = {"message": "Sync queued", "last_status_change": dt.now(UTC)}
        if row.iran_agent_key_hash:
            fields["iran_agent_command"] = "restart"
        if row.abroad_agent_key_hash:
            fields["abroad_agent_command"] = "restart"
        row = await update_hpx_nova(db, row, fields)
        return HpxNovaActionResponse(detail="Nova sync queued", nova=self._to_response(row))

    async def claim_agent(
        self,
        db: AsyncSession,
        *,
        model: HpxNovaAgentClaimRequest,
        panel_url: str | None,
    ) -> HpxNovaAgentBootstrap:
        token_hash = hash_api_key(model.join_token)
        found = await get_hpx_nova_by_join_token_hash(db, token_hash)
        if found is None:
            await self.raise_error(message="Invalid or expired Nova join token", code=401)
        row, side = found
        if model.side != side:
            await self.raise_error(message="Join token side mismatch", code=400)

        expires = row.iran_join_token_expires_at if side == "iran" else row.abroad_join_token_expires_at
        if expires and expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires and expires < dt.now(UTC):
            await self.raise_error(message="Nova join token expired", code=401)

        agent_key = _mint_token("hpxnk")
        identity = await self._decrypt_identity(db, row)
        config_toml = self._render(row, identity, side)
        fields = {
            f"{side}_agent_key_hash": hash_api_key(agent_key),
            f"{side}_agent_claimed_at": dt.now(UTC),
            f"{side}_agent_host": (model.host or "").strip() or None,
            f"{side}_join_token_hash": None,
            f"{side}_join_token_expires_at": None,
            f"{side}_agent_command": "start",
            "last_status_change": dt.now(UTC),
            "message": f"{side} agent claimed",
        }
        iran_ready = bool(row.iran_agent_key_hash) or side == "iran"
        abroad_ready = bool(row.abroad_agent_key_hash) or side == "abroad"
        if iran_ready and abroad_ready:
            fields["status"] = HpxNovaStatus.starting
        row = await update_hpx_nova(db, row, fields)
        return HpxNovaAgentBootstrap(
            nova_id=row.id,
            side=side,
            agent_key=agent_key,
            panel_url=(panel_url or "").rstrip("/"),
            engine_version=engine_mirror.engine_version(),
            config_toml=config_toml,
            command="start",
        )

    async def get_agent_config(
        self, db: AsyncSession, *, agent_key: str, side: str
    ) -> HpxNovaAgentConfigResponse:
        found = await get_hpx_nova_by_agent_key_hash(db, hash_api_key(agent_key))
        if found is None:
            await self.raise_error(message="Unauthorized Nova agent", code=401)
        row, bound_side = found
        if bound_side != side:
            await self.raise_error(message="Nova agent side mismatch", code=400)
        identity = await self._decrypt_identity(db, row)
        command = row.iran_agent_command if side == "iran" else row.abroad_agent_command
        return HpxNovaAgentConfigResponse(
            nova_id=row.id,
            side=side,
            config_toml=self._render(row, identity, side),
            command=command,
            engine_version=engine_mirror.engine_version(),
            enabled=bool(row.enabled),
        )

    async def agent_heartbeat(
        self,
        db: AsyncSession,
        *,
        agent_key: str,
        side: str,
        model: HpxNovaAgentHeartbeatRequest,
    ) -> dict:
        found = await get_hpx_nova_by_agent_key_hash(db, hash_api_key(agent_key))
        if found is None:
            await self.raise_error(message="Unauthorized Nova agent", code=401)
        row, bound_side = found
        if bound_side != side:
            await self.raise_error(message="Nova agent side mismatch", code=400)

        fields: dict = {
            f"{side}_agent_last_seen": dt.now(UTC),
        }
        if model.host:
            fields[f"{side}_agent_host"] = model.host.strip()
        if model.latency_ms is not None:
            fields["latency_ms"] = float(model.latency_ms)
        if model.message:
            fields["message"] = model.message[:1000]

        iran_online = side == "iran" or self._online(row.iran_agent_last_seen)
        abroad_online = side == "abroad" or self._online(row.abroad_agent_last_seen)
        if iran_online and abroad_online and row.enabled:
            fields["status"] = HpxNovaStatus.running
        elif iran_online or abroad_online:
            fields["status"] = HpxNovaStatus.partial
        row = await update_hpx_nova(db, row, fields)
        command = row.iran_agent_command if side == "iran" else row.abroad_agent_command
        return {"ok": True, "command": command, "status": row.status}

    async def agent_ack(
        self,
        db: AsyncSession,
        *,
        agent_key: str,
        side: str,
        model: HpxNovaAgentAckRequest,
    ) -> dict:
        found = await get_hpx_nova_by_agent_key_hash(db, hash_api_key(agent_key))
        if found is None:
            await self.raise_error(message="Unauthorized Nova agent", code=401)
        row, bound_side = found
        if bound_side != side:
            await self.raise_error(message="Nova agent side mismatch", code=400)

        fields: dict = {f"{side}_agent_command": None}
        if model.command == "leave":
            fields[f"{side}_agent_key_hash"] = None
            fields[f"{side}_agent_claimed_at"] = None
            fields[f"{side}_agent_last_seen"] = None
        await update_hpx_nova(db, row, fields)
        return {"ok": True}
