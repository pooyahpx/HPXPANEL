from __future__ import annotations

import logging

from fastapi import APIRouter

from . import (
    admin,
    admin_role,
    api_key,
    audit,
    backup,
    client_template,
    core,
    group,
    home,
    host,
    hpx_pulse,
    hpx_tunnel,
    hwid,
    node,
    observability,
    openvpn,
    settings,
    setup,
    subscription,
    system,
    user,
    user_template,
)

logger = logging.getLogger(__name__)

api_router = APIRouter()

routers = [
    home.router,
    admin.router,
    api_key.router,
    admin_role.router,
    audit.router,
    setup.router,
    system.router,
    settings.router,
    backup.router,
    group.router,
    core.router,
    client_template.router,
    host.router,
    node.router,
    observability.router,
    hpx_tunnel.router,
    hpx_pulse.router,
    openvpn.router,
    user.router,
    subscription.router,
    user_template.router,
    hwid.router,
]

try:
    from . import copilot

    routers.insert(-3, copilot.router)
except Exception as exc:
    logger.warning("HPX Copilot disabled — failed to load router: %s", exc)

for router in routers:
    api_router.include_router(router)

__all__ = ["api_router"]
