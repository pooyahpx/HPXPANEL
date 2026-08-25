from datetime import UTC, datetime as dt

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HpxTunnel, HpxTunnelRole, HpxTunnelStatus
from app.models.hpx_tunnel import HpxTunnelCreate, HpxTunnelUpdate
from app.services.hpx_tunnel.manager import container_name_for_tunnel


async def create_hpx_tunnel(
    db: AsyncSession,
    *,
    model: HpxTunnelCreate,
    password_encrypted: str,
) -> HpxTunnel:
    local_ip = model.local_ip
    if model.role == HpxTunnelRole.foreign and local_ip == "10.200.200.2":
        local_ip = "10.200.200.1"

    db_tunnel = HpxTunnel(
        name=model.name,
        role=model.role,
        status=HpxTunnelStatus.stopped,
        enabled=model.enabled,
        remote_ip=model.remote_ip,
        server_listen=model.server_listen,
        password_encrypted=password_encrypted,
        interface=model.interface,
        local_ip=local_ip,
        subnet=model.subnet,
        mtu=model.mtu,
        keepalive=model.keepalive,
        dscp_mark=model.dscp_mark,
        bandwidth_limit=model.bandwidth_limit,
        operating_mode=model.operating_mode,
        port_forwards=[item.model_dump() for item in model.port_forwards],
        docker_image=model.docker_image,
        backup_tunnel_id=model.backup_tunnel_id,
        auto_failover=model.auto_failover,
        priority=model.priority,
        alert_on_down=model.alert_on_down,
        note=model.note,
    )
    db.add(db_tunnel)
    await db.flush()
    db_tunnel.container_name = container_name_for_tunnel(db_tunnel.id)
    await db.flush()
    await db.refresh(db_tunnel)
    return db_tunnel


async def get_hpx_tunnel_by_id(db: AsyncSession, tunnel_id: int) -> HpxTunnel | None:
    return await db.get(HpxTunnel, tunnel_id)


async def get_hpx_tunnels_by_ids(db: AsyncSession, tunnel_ids: list[int]) -> list[HpxTunnel]:
    if not tunnel_ids:
        return []
    stmt = select(HpxTunnel).where(HpxTunnel.id.in_(tunnel_ids))
    return list((await db.execute(stmt)).scalars().all())


async def get_hpx_tunnels(
    db: AsyncSession,
    *,
    offset: int,
    limit: int,
    tunnel_id: int | None = None,
    name: str | None = None,
    role: HpxTunnelRole | None = None,
    status: HpxTunnelStatus | None = None,
) -> tuple[list[HpxTunnel], int]:
    filters = []
    if tunnel_id is not None:
        filters.append(HpxTunnel.id == tunnel_id)
    if name:
        filters.append(HpxTunnel.name.ilike(f"%{name}%"))
    if role is not None:
        filters.append(HpxTunnel.role == role)
    if status is not None:
        filters.append(HpxTunnel.status == status)

    count_stmt = select(func.count()).select_from(HpxTunnel)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = int((await db.execute(count_stmt)).scalar_one())

    stmt = select(HpxTunnel).order_by(HpxTunnel.priority.desc(), HpxTunnel.id.asc())
    if filters:
        stmt = stmt.where(*filters)
    stmt = stmt.offset(offset).limit(limit)
    rows = list((await db.execute(stmt)).scalars().all())
    return rows, total


async def update_hpx_tunnel(db: AsyncSession, db_tunnel: HpxTunnel, data: dict) -> HpxTunnel:
    for key, value in data.items():
        setattr(db_tunnel, key, value)
    await db.flush()
    await db.refresh(db_tunnel)
    return db_tunnel


async def delete_hpx_tunnel(db: AsyncSession, db_tunnel: HpxTunnel) -> None:
    await db.delete(db_tunnel)


async def apply_tunnel_update(db: AsyncSession, db_tunnel: HpxTunnel, model: HpxTunnelUpdate) -> HpxTunnel:
    data = model.model_dump(exclude_unset=True)
    if "port_forwards" in data and data["port_forwards"] is not None:
        data["port_forwards"] = [item.model_dump() for item in model.port_forwards or []]
    data.pop("password", None)
    return await update_hpx_tunnel(db, db_tunnel, data)


async def list_enabled_tunnels(db: AsyncSession) -> list[HpxTunnel]:
    stmt = select(HpxTunnel).where(HpxTunnel.enabled.is_(True)).order_by(HpxTunnel.priority.desc())
    return list((await db.execute(stmt)).scalars().all())
