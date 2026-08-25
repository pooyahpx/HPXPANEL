from fastapi import Query

from app.models.hpx_tunnel import HpxTunnelsQuery

from ._common import make_query_dependency

get_hpx_tunnel_list_query = make_query_dependency(
    HpxTunnelsQuery,
    field_overrides={
        "offset": Query(None),
        "limit": Query(None),
        "tunnel_id": Query(None),
        "name": Query(None),
        "role": Query(None),
        "status": Query(None),
    },
)
