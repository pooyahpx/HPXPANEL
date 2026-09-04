from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.utils.logger import get_logger
from config import cors_settings, server_settings

from .audit import AuditMiddleware
from .request_logging import RequestProcessTimeLoggingMiddleware


def setup_middleware(app: FastAPI):
    if server_settings.has_ssl:
        app.add_middleware(HTTPSRedirectMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuditMiddleware)
    app.add_middleware(RequestProcessTimeLoggingMiddleware, access_logger=get_logger("uvicorn.access"))
    # Starlette inserts newly-added middleware at the front of user_middleware,
    # making the last registration outermost. Proxy normalization must therefore
    # be registered last so AuditMiddleware observes the trusted client address.
    if server_settings.proxy_headers:
        app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=server_settings.forwarded_allow_ips)
