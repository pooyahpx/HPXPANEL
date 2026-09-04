import json

import pytest
from sqlalchemy.exc import DBAPIError, OperationalError
from starlette.requests import Request

from app import app_factory
from app.app_factory import database_operational_error_handler


@pytest.mark.asyncio
async def test_database_operational_error_handler_returns_503():
    request = Request({"type": "http", "method": "GET", "path": "/sub/token", "headers": []})
    exc = OperationalError(None, None, Exception("connection failed"))

    response = await database_operational_error_handler(request, exc)

    assert response.status_code == 503
    assert json.loads(response.body) == {"detail": "Database temporarily unavailable"}


@pytest.mark.asyncio
async def test_database_operational_error_handler_handles_dbapi_errors():
    request = Request({"type": "http", "method": "GET", "path": "/sub/token", "headers": []})
    exc = DBAPIError(None, None, Exception("connection failed"))

    response = await database_operational_error_handler(request, exc)

    assert response.status_code == 503
    assert json.loads(response.body) == {"detail": "Database temporarily unavailable"}


def test_multiworker_startup_requires_nats(monkeypatch):
    monkeypatch.setattr(app_factory.server_settings, "workers", 2)
    monkeypatch.setattr(app_factory, "is_nats_enabled", lambda: False)

    with pytest.raises(RuntimeError, match="UVICORN_WORKERS"):
        app_factory.create_app()
