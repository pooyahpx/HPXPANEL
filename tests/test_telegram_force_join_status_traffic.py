"""v4.10.6 Telegram: force join gate, server status matching, admin traffic math, test-claim reset, migration."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from alembic.command import downgrade, upgrade
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.crud.shop import count_test_claimed, reset_all_test_claimed, reset_test_claimed
from app.db.models import TelegramProfile
from app.telegram.utils.admin_traffic import (
    GB_BYTES,
    compute_data_limit,
    parse_remaining_input,
    remaining_bytes,
)
from app.telegram.utils.force_join import (
    force_join_required,
    is_channel_member,
    is_joined_status,
    normalize_channel_id,
    user_passes_force_join,
)
from app.telegram.utils.server_status import (
    CONNECTING,
    OFFLINE,
    ONLINE,
    UNKNOWN,
    NodeInfo,
    build_server_status_rows,
    match_host_state,
    node_status_to_state,
)

# ---------------------------------------------------------------- force join


def _bot_with_status(status, is_member=None):
    bot = AsyncMock()
    bot.get_chat_member.return_value = SimpleNamespace(status=status, is_member=is_member)
    return bot


@pytest.mark.parametrize("status", ["creator", "administrator", "member", "restricted"])
def test_joined_statuses(status):
    assert is_joined_status(status) is True


@pytest.mark.parametrize("status", ["left", "kicked", "", None])
def test_not_joined_statuses(status):
    assert is_joined_status(status) is False


@pytest.mark.asyncio
async def test_gate_member_allowed_left_blocked():
    assert await is_channel_member(_bot_with_status("member"), "@chan", 1) is True
    assert await is_channel_member(_bot_with_status("left"), "@chan", 1) is False
    assert await is_channel_member(_bot_with_status("kicked"), "@chan", 1) is False


@pytest.mark.asyncio
async def test_gate_restricted_who_left_is_blocked():
    assert await is_channel_member(_bot_with_status("restricted", True), "@chan", 1) is True
    assert await is_channel_member(_bot_with_status("restricted", False), "@chan", 1) is False


@pytest.mark.asyncio
async def test_gate_numeric_channel_is_int_and_api_error_fails_open():
    bot = _bot_with_status("member")
    await is_channel_member(bot, "-1001234567890", 5)
    bot.get_chat_member.assert_awaited_with(-1001234567890, 5)
    broken = AsyncMock()
    broken.get_chat_member.side_effect = RuntimeError("chat not found")
    assert await is_channel_member(broken, "@chan", 1) is True


@pytest.mark.asyncio
async def test_gate_toggle_off_skips_check_entirely():
    bot = _bot_with_status("left")
    off = SimpleNamespace(enabled=True, force_join_enabled=False, force_join_channel_id="@chan")
    assert await user_passes_force_join(bot, off, 1) is True
    bot.get_chat_member.assert_not_awaited()

    no_channel = SimpleNamespace(enabled=True, force_join_enabled=True, force_join_channel_id=None)
    assert force_join_required(no_channel) is False

    shop_off = SimpleNamespace(enabled=False, force_join_enabled=True, force_join_channel_id="@chan")
    assert force_join_required(shop_off) is False

    on = SimpleNamespace(enabled=True, force_join_enabled=True, force_join_channel_id="@chan")
    assert await user_passes_force_join(bot, on, 1) is False
    bot.get_chat_member.assert_awaited_once()


def test_normalize_channel_id():
    assert normalize_channel_id("@my_channel") == "@my_channel"
    assert normalize_channel_id("my_channel") == "@my_channel"
    assert normalize_channel_id("https://t.me/my_channel") == "@my_channel"
    assert normalize_channel_id("-1001234567890") == "-1001234567890"
    assert normalize_channel_id("-۱۰۰۱۲۳۴۵۶۷۸۹۰") == "-1001234567890"
    assert normalize_channel_id("https://t.me/+AbCdEf") is None
    assert normalize_channel_id("12") is None
    assert normalize_channel_id("") is None


# -------------------------------------------------------------- server status


def test_node_status_mapping():
    assert node_status_to_state("connected") == ONLINE
    assert node_status_to_state("limited") == ONLINE
    assert node_status_to_state("connecting") == CONNECTING
    assert node_status_to_state("error") == OFFLINE
    assert node_status_to_state("disabled") == OFFLINE


def test_match_host_to_node():
    nodes = [
        NodeInfo("de-1", "de1.example.com", "connected"),
        NodeInfo("nl-1", "10.0.0.5", "error"),
        NodeInfo("fr-1", "fr1.example.com", "connecting"),
    ]
    assert match_host_state(["de1.example.com"], nodes) == ONLINE
    assert match_host_state(["DE1.example.com "], nodes) == ONLINE  # case/space insensitive
    assert match_host_state(["10.0.0.5"], nodes) == OFFLINE
    assert match_host_state(["fr1.example.com"], nodes) == CONNECTING
    assert match_host_state(["edge.de1.example.com"], nodes) == ONLINE  # contained
    assert match_host_state(["de-1"], nodes) == ONLINE  # node name
    assert match_host_state(["other.example.org"], nodes) == UNKNOWN
    assert match_host_state(["{SERVER_IP}"], nodes) == UNKNOWN
    assert match_host_state([], nodes) == UNKNOWN
    assert match_host_state(["de1.example.com"], []) == UNKNOWN


def test_match_prefers_best_state_among_matches():
    nodes = [NodeInfo("a", "x.example.com", "error"), NodeInfo("b", "x.example.com", "connected")]
    assert match_host_state(["x.example.com"], nodes) == ONLINE


def test_build_rows_dedupes_by_remark():
    nodes = [NodeInfo("a", "a.example.com", "connected")]
    rows = build_server_status_rows(
        [
            ("Germany", ["a.example.com"]),
            ("Germany", ["zzz.example.com"]),
            ("Unknown host", ["q.example.com"]),
        ],
        nodes,
    )
    assert rows == [("Germany", ONLINE), ("Unknown host", UNKNOWN)]


# --------------------------------------------------------------- admin traffic


def test_remaining_to_data_limit_math():
    used = 10 * GB_BYTES
    assert compute_data_limit(used, parse_remaining_input("5")) == 15 * GB_BYTES
    assert compute_data_limit(used, parse_remaining_input("2.5")) == used + int(2.5 * GB_BYTES)
    assert compute_data_limit(used, parse_remaining_input("۵")) == 15 * GB_BYTES
    assert compute_data_limit(used, parse_remaining_input("0")) == 0  # 0 = unlimited
    assert compute_data_limit(used, parse_remaining_input("unlimited")) == 0
    assert compute_data_limit(used, parse_remaining_input("نامحدود")) == 0
    assert compute_data_limit(0, parse_remaining_input("1")) == GB_BYTES


def test_remaining_input_rejects_garbage():
    for bad in ("", "abc", "-3"):
        with pytest.raises(ValueError):
            parse_remaining_input(bad)


def test_remaining_bytes():
    assert remaining_bytes(3 * GB_BYTES, 10 * GB_BYTES) == 7 * GB_BYTES
    assert remaining_bytes(12 * GB_BYTES, 10 * GB_BYTES) == 0
    assert remaining_bytes(3, None) is None
    assert remaining_bytes(3, 0) is None


# ------------------------------------------------------------ test claim reset


@pytest.fixture
async def session(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'tg.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(TelegramProfile.__table__.create)
    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as db:
        db.add_all(
            [
                TelegramProfile(telegram_id=1, test_claimed=True),
                TelegramProfile(telegram_id=2, test_claimed=True),
                TelegramProfile(telegram_id=3, test_claimed=False),
            ]
        )
        await db.commit()
        yield db
    await engine.dispose()


@pytest.mark.asyncio
async def test_reset_test_claimed_flips_flag(session):
    assert await count_test_claimed(session) == 2
    assert await reset_test_claimed(session, 1) is True
    assert (await session.get(TelegramProfile, 1)).test_claimed is False
    assert (await session.get(TelegramProfile, 2)).test_claimed is True
    assert await reset_test_claimed(session, 999) is False


@pytest.mark.asyncio
async def test_reset_all_test_claimed(session):
    assert await reset_all_test_claimed(session) == 2
    assert await count_test_claimed(session) == 0
    assert await reset_all_test_claimed(session, admin_id=7) == 0


# ------------------------------------------------------------------ migration


def test_force_join_status_migration_upgrade_and_downgrade(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'fj-migration.db'}")
    with engine.begin() as connection:
        config = Config("alembic.ini")
        config.attributes["connection"] = connection
        upgrade(config, "head")
        cols = {c["name"] for c in inspect(connection).get_columns("shop_configs")}
        assert {
            "force_join_enabled",
            "force_join_channel_id",
            "force_join_channel_url",
            "server_status_enabled",
            "server_status_group_id",
        }.issubset(cols)

        downgrade(config, "aa1bb2cc3dd4")
        cols = {c["name"] for c in inspect(connection).get_columns("shop_configs")}
        assert "force_join_enabled" not in cols
        assert "server_status_group_id" not in cols
        upgrade(config, "head")


# ------------------------------------------------------------- middleware gate


@pytest.mark.asyncio
async def test_force_join_middleware_blocks_non_member_and_bypasses_admin():
    from unittest.mock import patch

    from aiogram.types import Message

    from app.telegram.middlewares import force_join as fj

    config = SimpleNamespace(
        enabled=True,
        force_join_enabled=True,
        force_join_channel_id="@chan",
        force_join_channel_url="https://t.me/chan",
    )
    db = AsyncMock()
    mw = fj.ForceJoinMiddleware()

    async def run(admin, status):
        handler = AsyncMock(return_value="handled")
        event = AsyncMock(spec=Message)
        event.from_user = SimpleNamespace(id=42)
        event.text = "/start"
        event.answer = AsyncMock()
        data = {"admin": admin, "db": db, "bot": _bot_with_status(status), "state": None}
        result = await mw(handler, event, data)
        return result, handler, event

    with (
        patch.object(fj, "get_buyer_shop_config", new=AsyncMock(return_value=config)),
        patch.object(fj, "get_telegram_lang", new=AsyncMock(return_value="en")),
    ):
        result, handler, _ = await run(None, "member")
        assert result == "handled" and handler.await_count == 1

        result, handler, event = await run(None, "left")
        assert result is None and handler.await_count == 0
        event.answer.assert_awaited_once()

        result, handler, _ = await run(SimpleNamespace(id=1), "left")  # panel admin bypass
        assert result == "handled" and handler.await_count == 1

    off = SimpleNamespace(enabled=True, force_join_enabled=False, force_join_channel_id="@chan")
    with patch.object(fj, "get_buyer_shop_config", new=AsyncMock(return_value=off)):
        result, handler, _ = await run(None, "left")  # toggle OFF -> gate skipped
        assert result == "handled" and handler.await_count == 1