from fastapi import APIRouter, Depends, status
from starlette.responses import PlainTextResponse, Response

from app.db import AsyncSession, get_db
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
from app.operation import OperatorType
from app.operation.hpx_tunnel import HpxTunnelOperation
from app.routers.dependencies import get_hpx_tunnel_list_query
from app.utils import responses

from .authentication import require_permission

router = APIRouter(
    tags=["HPX ICMP Tunnels"],
    prefix="/api/hpx_tunnel",
    responses={401: responses._401, 403: responses._403},
)

hpx_tunnel_operator = HpxTunnelOperation(operator_type=OperatorType.API)


@router.post(
    "",
    response_model=HpxTunnelActionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={409: responses._409, 422: responses._422},
)
async def create_hpx_tunnel(
    model: HpxTunnelCreate,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_tunnels", "create")),
):
    return await hpx_tunnel_operator.create_tunnel(db, admin=admin, model=model)


@router.get("s", response_model=HpxTunnelsResponse)
async def list_hpx_tunnels(
    query: HpxTunnelsQuery = Depends(get_hpx_tunnel_list_query),
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_tunnels", "read")),
):
    return await hpx_tunnel_operator.list_tunnels(db, admin=admin, query=query)


@router.post(
    "s/bulk/delete",
    response_model=RemoveHpxTunnelsResponse,
    responses={404: responses._404},
)
async def bulk_delete_hpx_tunnels(
    bulk: BulkHpxTunnelSelection,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_tunnels", "delete")),
):
    return await hpx_tunnel_operator.bulk_delete_tunnels(db, admin=admin, bulk=bulk)


@router.get("/{tunnel_id}", response_model=HpxTunnelResponse, responses={404: responses._404})
async def get_hpx_tunnel(
    tunnel_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_tunnels", "read")),
):
    return await hpx_tunnel_operator.get_tunnel(db, admin=admin, tunnel_id=tunnel_id)


@router.patch("/{tunnel_id}", response_model=HpxTunnelResponse, responses={404: responses._404, 409: responses._409})
async def modify_hpx_tunnel(
    tunnel_id: int,
    model: HpxTunnelUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_tunnels", "update")),
):
    return await hpx_tunnel_operator.modify_tunnel(db, admin=admin, tunnel_id=tunnel_id, model=model)


@router.delete("/{tunnel_id}", status_code=status.HTTP_204_NO_CONTENT, responses={404: responses._404})
async def remove_hpx_tunnel(
    tunnel_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_tunnels", "delete")),
):
    await hpx_tunnel_operator.delete_tunnel(db, admin=admin, tunnel_id=tunnel_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{tunnel_id}/start", response_model=HpxTunnelActionResponse, responses={404: responses._404})
async def start_hpx_tunnel(
    tunnel_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_tunnels", "start")),
):
    return await hpx_tunnel_operator.start_tunnel_action(db, admin=admin, tunnel_id=tunnel_id)


@router.post("/{tunnel_id}/stop", response_model=HpxTunnelActionResponse, responses={404: responses._404})
async def stop_hpx_tunnel(
    tunnel_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_tunnels", "stop")),
):
    return await hpx_tunnel_operator.stop_tunnel_action(db, admin=admin, tunnel_id=tunnel_id)


@router.post("/{tunnel_id}/restart", response_model=HpxTunnelActionResponse, responses={404: responses._404})
async def restart_hpx_tunnel(
    tunnel_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_tunnels", "restart")),
):
    return await hpx_tunnel_operator.restart_tunnel_action(db, admin=admin, tunnel_id=tunnel_id)


@router.get("/{tunnel_id}/stats", response_model=HpxTunnelStatsResponse, responses={404: responses._404})
async def get_hpx_tunnel_stats(
    tunnel_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_tunnels", "stats")),
):
    return await hpx_tunnel_operator.get_tunnel_stats(db, admin=admin, tunnel_id=tunnel_id)


@router.get("/{tunnel_id}/logs", response_class=PlainTextResponse, responses={404: responses._404})
async def get_hpx_tunnel_logs(
    tunnel_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(require_permission("hpx_tunnels", "logs")),
):
    return await hpx_tunnel_operator.get_tunnel_logs(db, admin=admin, tunnel_id=tunnel_id)
