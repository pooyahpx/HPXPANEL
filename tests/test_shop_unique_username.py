from unittest.mock import AsyncMock, patch

import pytest

from app.operation.shop import allocate_unique_shop_username, append_random_username_digits


def test_append_random_username_digits_keeps_base_and_adds_digits():
    out = append_random_username_digits("PS3TC")
    assert out.startswith("PS3TC")
    assert out[5:].isdigit()
    assert 3 <= len(out) <= 128


def test_append_random_username_digits_respects_max_length():
    base = "a" * 130
    out = append_random_username_digits(base, digits=4)
    assert len(out) <= 128
    assert out[-4:].isdigit()


@pytest.mark.asyncio
async def test_allocate_unique_shop_username_uses_preferred_when_free():
    db = AsyncMock()
    with patch("app.operation.shop.get_existing_usernames", new=AsyncMock(return_value=set())):
        assert await allocate_unique_shop_username(db, "PS3TC") == "PS3TC"


@pytest.mark.asyncio
async def test_allocate_unique_shop_username_appends_digits_when_taken():
    db = AsyncMock()
    with patch("app.operation.shop.get_existing_usernames", new=AsyncMock(return_value={"PS3TC"})):
        name = await allocate_unique_shop_username(db, "PS3TC")
    assert name != "PS3TC"
    assert name.startswith("PS3TC")
    assert name[5:].isdigit()
