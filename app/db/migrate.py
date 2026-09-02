"""Apply pending Alembic migrations before the panel serves traffic."""

from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

from app.utils.logger import get_logger
from config import database_settings

logger = get_logger("db-migrate")


def _sync_database_url(url: str) -> str:
    if "sqlite+aiosqlite" in url:
        return url.replace("sqlite+aiosqlite", "sqlite")
    if "postgresql+asyncpg" in url:
        return url.replace("postgresql+asyncpg", "postgresql")
    if "mysql+asyncmy" in url:
        return url.replace("mysql+asyncmy", "mysql+pymysql")
    return url


def _alembic_config() -> Config:
    root = Path(__file__).resolve().parents[2]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", _sync_database_url(database_settings.url))
    return cfg


def run_pending_migrations_sync() -> None:
    cfg = _alembic_config()
    sync_url = cfg.get_main_option("sqlalchemy.url")
    logger.info("Applying database migrations for %s", sync_url)
    with create_engine(sync_url).connect() as connection:
        cfg.attributes["connection"] = connection
        try:
            command.upgrade(cfg, "head")
        finally:
            cfg.attributes.pop("connection", None)
    logger.info("Database migrations are up to date")


async def run_pending_migrations() -> None:
    await asyncio.to_thread(run_pending_migrations_sync)
