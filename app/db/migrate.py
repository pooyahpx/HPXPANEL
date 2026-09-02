"""Apply pending Alembic migrations before the panel serves traffic."""

from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.utils.logger import get_logger
from config import database_settings

logger = get_logger("db-migrate")


def _alembic_config() -> Config:
    root = Path(__file__).resolve().parents[2]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", database_settings.url)
    return cfg


def run_pending_migrations_sync() -> None:
    cfg = _alembic_config()
    logger.info("Applying database migrations for %s", database_settings.url)
    command.upgrade(cfg, "head")
    logger.info("Database migrations are up to date")


async def run_pending_migrations() -> None:
    await asyncio.to_thread(run_pending_migrations_sync)
