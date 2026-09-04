from datetime import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HpxPulse, HpxPulseStatus
from app.models.hpx_pulse import HpxPulseCreate
from app.utils.crypto import hash_api_key


async def create_hpx_pulse(
    db: AsyncSession,
    *,
    model: HpxPulseCreate,
    token_encrypted: str,
    profile_id: str,
    tunnel_mode: str,
    carrier: str | None,
    preset: str,
    advice_json: dict | None,
) -> HpxPulse:
    db_pulse = HpxPulse(
        name=model.name,
        status=HpxPulseStatus.pending_claim,
        enabled=True,
        engine="hpx",
        profile_id=profile_id,
        goal=model.goal,
        tunnel_mode=tunnel_mode,
        carrier=carrier,
        preset=preset,
        token_encrypted=token_encrypted,
        iran_public_ip=model.iran_public_ip,
        abroad_public_ip=model.abroad_public_ip,
        control_port=model.control_port,
        port_forwards=model.port_forwards,
        domain=model.domain,
        sni_hint=model.sni_hint,
        advice_json=advice_json,
        note=model.note,
        auto_restart_interval_minutes=(
            model.auto_restart_interval_minutes if model.auto_restart_interval_minutes and model.auto_restart_interval_minutes > 0 else None
        ),
    )
    db.add(db_pulse)
    await db.flush()
    await db.refresh(db_pulse)
    return db_pulse


async def get_hpx_pulse_by_id(db: AsyncSession, pulse_id: int) -> HpxPulse | None:
    return await db.get(HpxPulse, pulse_id)


async def get_hpx_pulse_by_join_token_hash(db: AsyncSession, token_hash: str, side: str) -> HpxPulse | None:
    col = HpxPulse.iran_join_token_hash if side == "iran" else HpxPulse.abroad_join_token_hash
    stmt = select(HpxPulse).where(col == token_hash)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_hpx_pulse_by_agent_key_hash(db: AsyncSession, key_hash: str, side: str) -> HpxPulse | None:
    col = HpxPulse.iran_agent_key_hash if side == "iran" else HpxPulse.abroad_agent_key_hash
    stmt = select(HpxPulse).where(col == key_hash)
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_hpx_pulses(
    db: AsyncSession,
    *,
    offset: int,
    limit: int,
    name: str | None = None,
) -> tuple[list[HpxPulse], int]:
    filters = []
    if name:
        filters.append(HpxPulse.name.ilike(f"%{name}%"))

    count_stmt = select(func.count()).select_from(HpxPulse)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = int((await db.execute(count_stmt)).scalar_one())

    stmt = select(HpxPulse).order_by(HpxPulse.id.desc())
    if filters:
        stmt = stmt.where(*filters)
    stmt = stmt.offset(offset).limit(limit)
    rows = list((await db.execute(stmt)).scalars().all())
    return rows, total


async def update_hpx_pulse(db: AsyncSession, db_pulse: HpxPulse, data: dict) -> HpxPulse:
    for key, value in data.items():
        setattr(db_pulse, key, value)
    await db.flush()
    await db.refresh(db_pulse)
    return db_pulse


async def delete_hpx_pulse(db: AsyncSession, db_pulse: HpxPulse) -> None:
    await db.delete(db_pulse)


def set_join_token(db_pulse: HpxPulse, *, side: str, token: str, expires_at: dt) -> None:
    token_hash = hash_api_key(token)
    if side == "iran":
        db_pulse.iran_join_token_hash = token_hash
        db_pulse.iran_join_token_expires_at = expires_at
    else:
        db_pulse.abroad_join_token_hash = token_hash
        db_pulse.abroad_join_token_expires_at = expires_at
