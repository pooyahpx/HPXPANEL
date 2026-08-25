from datetime import UTC, datetime as dt

from sqlalchemy.exc import IntegrityError

from app.db import AsyncSession
from app.db.crud.general import get_jwt_secret_key
from app.db.crud.hpx_tunnel import (
    create_hpx_tunnel,
    delete_hpx_tunnel,
    get_hpx_tunnel_by_id,
    get_hpx_tunnels,
    get_hpx_tunnels_by_ids,
    update_hpx_tunnel,
)
from app.db.models import HpxTunnel, HpxTunnelRole, HpxTunnelStatus
from app.models.admin import AdminDetails
from app.models.hpx_tunnel import (
    BulkHpxTunnelSelection,
    HpxTunnelActionResponse,
    HpxTunnelCreate,
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
from app.utils.crypto import decrypt_secret, encrypt_secret


def _to_response(db_tunnel: HpxTunnel) -> HpxTunnelResponse:
    return HpxTunnelResponse.model_validate(
        {
            **HpxTunnelResponse.model_validate(db_tunnel).model_dump(),
            "has_password": bool(db_tunnel.password_encrypted),
        }
    )


class HpxTunnelOperation(BaseOperation):
    async def _secret_key(self, db: AsyncSession) -> str:
        return await get_jwt_secret_key(db)

    async def _decrypt_password(self, db: AsyncSession, db_tunnel: HpxTunnel) -> str:
        secret = await self._secret_key(db)
        return decrypt_secret(db_tunnel.password_encrypted, secret)

    async def _encrypt_password(self, db: AsyncSession, password: str) -> str:
        secret = await self._secret_key(db)
        return encrypt_secret(password, secret)

    async def _refresh_runtime(
        self,
        db: AsyncSession,
        db_tunnel: HpxTunnel,
        *,
        ping: bool = True,
    ) -> HpxTunnel:
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
        self, db: AsyncSession, *, admin: AdminDetails, model: HpxTunnelCreate
    ) -> HpxTunnelActionResponse:
        if not is_linux_host():
            await self.raise_error(
                message="HPX tunnels can only be managed on Linux hosts with Docker",
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

        message = None
        if model.start_after_create:
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

        return HpxTunnelActionResponse(tunnel=_to_response(db_tunnel), message=message)

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

        db_tunnel = await update_hpx_tunnel(db, db_tunnel, update_data)
        await db.commit()
        return _to_response(db_tunnel)

    async def delete_tunnel(self, db: AsyncSession, *, admin: AdminDetails, tunnel_id: int) -> None:
        db_tunnel = await get_hpx_tunnel_by_id(db, tunnel_id)
        if db_tunnel is None:
            await self.raise_error(message="Tunnel not found", code=404)

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
        return await get_container_logs(db_tunnel.container_name)
