import hashlib
import json
import secrets
from datetime import UTC, datetime as dt, timedelta as td

from sqlalchemy.exc import IntegrityError

from app.db import AsyncSession
from app.db.crud.general import get_jwt_secret_key
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
    HpxPulseResponse,
    HpxPulsesResponse,
    PulseAdviseRequest,
    PulseAdviseResponse,
)
from app.operation import BaseOperation
from app.services.hpx_pulse.advisor import advise, profile_meta
from app.services.hpx_pulse.backpack_render import mint_backpack_token, render_for_side
from app.utils.crypto import decrypt_secret, encrypt_secret, hash_api_key

JOIN_TOKEN_TTL_HOURS = 24
AGENT_SCRIPT_URL = "https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/scripts/hpx-pulse-agent.sh"


def _mint_token(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def _config_hash(toml: str, side: str, pulse_id: int) -> str:
    canonical = json.dumps({"toml": toml, "side": side, "pulse_id": pulse_id}, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _build_join_command(panel_url: str | None, token: str, side: str) -> str:
    base = (panel_url or "https://YOUR_PANEL_HOST").rstrip("/")
    return (
        f"curl -fsSL {AGENT_SCRIPT_URL} | sudo bash -s -- join {token} "
        f"--panel-url {base} --side {side}"
    )


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
        advice = PulseAdviseResponse.model_validate(db_pulse.advice_json)
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
        "created_at": db_pulse.created_at,
    }
    return HpxPulseResponse.model_validate(data)


def _desired_status(db_pulse: HpxPulse) -> str:
    if not db_pulse.enabled:
        return HpxPulseStatus.stopped.value
    return HpxPulseStatus.running.value


class HpxPulseOperation(BaseOperation):
    async def _secret_key(self, db: AsyncSession) -> str:
        return await get_jwt_secret_key(db)

    async def _encrypt_token(self, db: AsyncSession, token: str) -> str:
        secret = await self._secret_key(db)
        return encrypt_secret(token, secret)

    async def _decrypt_token(self, db: AsyncSession, db_pulse: HpxPulse) -> str:
        secret = await self._secret_key(db)
        return decrypt_secret(db_pulse.token_encrypted, secret)

    async def advise_pulse(self, model: PulseAdviseRequest, *, domain: str | None = None, sni_hint: str | None = None) -> PulseAdviseResponse:
        return advise(model, domain=domain, sni_hint=sni_hint)

    async def _issue_join_tokens(
        self, db: AsyncSession, db_pulse: HpxPulse, *, panel_url: str | None
    ) -> tuple[str, str, str, str, dt]:
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
        iran_cmd = _build_join_command(panel_url, iran_token, "iran")
        abroad_cmd = _build_join_command(panel_url, abroad_token, "abroad")
        return iran_token, iran_cmd, abroad_token, abroad_cmd, expires_at

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

        backpack_token = mint_backpack_token()
        token_encrypted = await self._encrypt_token(db, backpack_token)

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
            iran_t, iran_c, abroad_t, abroad_c, exp = await self._issue_join_tokens(db, db_pulse, panel_url=panel_url)
            await db.commit()
        except IntegrityError:
            await db.rollback()
            await self.raise_error(message="Pulse name already exists", code=409)

        return HpxPulseActionResponse(
            pulse=_to_response(db_pulse),
            message="Pulse created — run join commands on Iran and abroad servers",
            iran_join_token=iran_t,
            iran_join_command=iran_c,
            abroad_join_token=abroad_t,
            abroad_join_command=abroad_c,
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
        iran_t, iran_c, abroad_t, abroad_c, exp = await self._issue_join_tokens(db, db_pulse, panel_url=panel_url)
        await db.commit()
        return HpxPulseActionResponse(
            pulse=_to_response(db_pulse),
            iran_join_token=iran_t,
            iran_join_command=iran_c,
            abroad_join_token=abroad_t,
            abroad_join_command=abroad_c,
            iran_join_expires_at=exp,
            abroad_join_expires_at=exp,
            message="Join tokens regenerated",
        )

    async def claim_agent(self, db: AsyncSession, *, model: HpxPulseAgentClaimRequest) -> HpxPulseAgentBootstrap:
        side = model.side
        token_hash = hash_api_key(model.join_token)
        db_pulse = await get_hpx_pulse_by_join_token_hash(db, token_hash, side)
        if db_pulse is None:
            await self.raise_error(message="Invalid join token", code=401)

        exp = db_pulse.iran_join_token_expires_at if side == "iran" else db_pulse.abroad_join_token_expires_at
        if exp and exp < dt.now(UTC):
            await self.raise_error(message="Join token expired", code=401)

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
                {"status": HpxPulseStatus.starting, "message": "Both agents claimed — starting tunnel"},
            )
        else:
            db_pulse = await update_hpx_pulse(
                db,
                db_pulse,
                {"status": HpxPulseStatus.partial, "message": f"{side} claimed — waiting for other side"},
            )
        await db.commit()

        return HpxPulseAgentBootstrap(
            pulse_id=db_pulse.id,
            name=db_pulse.name,
            side=side,
            agent_key=agent_key,
            backpack_toml=toml,
            config_hash=cfg_hash,
            control_port=db_pulse.control_port,
            abroad_public_ip=db_pulse.abroad_public_ip,
            iran_public_ip=db_pulse.iran_public_ip,
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
            backpack_toml=toml,
            config_hash=_config_hash(toml, side, db_pulse.id),
            desired_status=_desired_status(db_pulse),
            agent_command=db_pulse.iran_agent_command if side == "iran" else db_pulse.abroad_agent_command,
            enabled=db_pulse.enabled,
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
            "latency_ms": model.latency_ms,
            "packet_loss_pct": model.packet_loss_pct,
            "message": model.message,
        }
        if model.status in {HpxPulseStatus.running.value, "running"} and db_pulse.iran_agent_key_hash and db_pulse.abroad_agent_key_hash:
            update_data["status"] = HpxPulseStatus.running
        db_pulse = await update_hpx_pulse(db, db_pulse, update_data)
        await db.commit()
        return self._agent_config(db_pulse, side, token)

    async def agent_ack(
        self, db: AsyncSession, *, agent_key: str, side: str, model: HpxPulseAgentAckRequest
    ) -> None:
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
