from datetime import UTC, datetime as dt

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HpxNova, HpxNovaStatus
from app.utils.crypto import hash_api_key


async def create_hpx_nova(
    db: AsyncSession,
    *,
    name: str,
    identity_encrypted: str,
    iran_public_ip: str,
    abroad_public_ip: str,
    carrier: str,
    lanes: int,
    resume: bool,
    tunnel_port: int,
    sni: str | None,
    ws_path: str | None,
    port_forwards: list[str] | None,
    proxy_listen: str | None,
    note: str | None,
) -> HpxNova:
    row = HpxNova(
        name=name,
        identity_encrypted=identity_encrypted,
        iran_public_ip=iran_public_ip,
        abroad_public_ip=abroad_public_ip,
        carrier=carrier,
        lanes=lanes,
        resume=resume,
        tunnel_port=tunnel_port,
        sni=sni,
        ws_path=ws_path,
        port_forwards=port_forwards or [],
        proxy_listen=proxy_listen,
        note=note,
        status=HpxNovaStatus.pending_claim,
        engine="nova",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_hpx_nova_by_id(db: AsyncSession, nova_id: int) -> HpxNova | None:
    return await db.get(HpxNova, nova_id)


async def get_hpx_novas(
    db: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 50,
    name: str | None = None,
) -> tuple[list[HpxNova], int]:
    base = select(HpxNova)
    if name:
        base = base.where(HpxNova.name == name)
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one() or 0)
    rows = list(
        (await db.execute(base.order_by(HpxNova.id.desc()).offset(offset).limit(limit))).scalars().all()
    )
    return rows, total


async def update_hpx_nova(db: AsyncSession, row: HpxNova, fields: dict) -> HpxNova:
    for key, value in fields.items():
        setattr(row, key, value)
    await db.commit()
    await db.refresh(row)
    return row


async def delete_hpx_nova(db: AsyncSession, row: HpxNova) -> None:
    await db.delete(row)
    await db.commit()


def set_join_token(row: HpxNova, *, side: str, token: str, expires_at: dt) -> None:
    digest = hash_api_key(token)
    if side == "iran":
        row.iran_join_token_hash = digest
        row.iran_join_token_expires_at = expires_at
    else:
        row.abroad_join_token_hash = digest
        row.abroad_join_token_expires_at = expires_at


async def get_hpx_nova_by_join_token_hash(db: AsyncSession, token_hash: str) -> tuple[HpxNova, str] | None:
    iran = (
        await db.execute(select(HpxNova).where(HpxNova.iran_join_token_hash == token_hash).limit(1))
    ).scalar_one_or_none()
    if iran is not None:
        return iran, "iran"
    abroad = (
        await db.execute(select(HpxNova).where(HpxNova.abroad_join_token_hash == token_hash).limit(1))
    ).scalar_one_or_none()
    if abroad is not None:
        return abroad, "abroad"
    return None


async def get_hpx_nova_by_agent_key_hash(db: AsyncSession, key_hash: str) -> tuple[HpxNova, str] | None:
    iran = (
        await db.execute(select(HpxNova).where(HpxNova.iran_agent_key_hash == key_hash).limit(1))
    ).scalar_one_or_none()
    if iran is not None:
        return iran, "iran"
    abroad = (
        await db.execute(select(HpxNova).where(HpxNova.abroad_agent_key_hash == key_hash).limit(1))
    ).scalar_one_or_none()
    if abroad is not None:
        return abroad, "abroad"
    return None


async def clear_stale_join_hashes(db: AsyncSession) -> None:
    now = dt.now(UTC)
    await db.execute(
        update(HpxNova)
        .where(HpxNova.iran_join_token_expires_at.is_not(None), HpxNova.iran_join_token_expires_at < now)
        .values(iran_join_token_hash=None, iran_join_token_expires_at=None)
    )
    await db.execute(
        update(HpxNova)
        .where(HpxNova.abroad_join_token_expires_at.is_not(None), HpxNova.abroad_join_token_expires_at < now)
        .values(abroad_join_token_hash=None, abroad_join_token_expires_at=None)
    )
    await db.commit()
