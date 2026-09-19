"""P1 shop: multi-shop preference, payment filters, revenue ledger."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_buyer_shop_config_deep_link_and_preferred():
    # Import inside test after patching heavy telegram package is avoided by
    # loading the helper module path that CI uses with full deps.
    from app.telegram.utils import shop_helpers as sh

    shop_a = SimpleNamespace(admin_id=10, enabled=True)
    shop_b = SimpleNamespace(admin_id=20, enabled=True)
    db = AsyncMock()
    profile = SimpleNamespace(preferred_shop_admin_id=20)

    with (
        patch.object(sh, "get_enabled_shop_config_by_admin_username", new=AsyncMock(return_value=shop_a)) as by_name,
        patch.object(sh, "set_preferred_shop_admin", new=AsyncMock(return_value=profile)) as set_pref,
        patch.object(sh, "get_or_create_telegram_profile", new=AsyncMock(return_value=profile)),
        patch.object(sh, "get_shop_config_by_admin", new=AsyncMock(return_value=shop_b)),
        patch.object(
            sh,
            "list_enabled_shop_configs",
            new=AsyncMock(return_value=[(shop_a, MagicMock()), (shop_b, MagicMock())]),
        ),
    ):
        resolved = await sh.get_buyer_shop_config(
            db, telegram_id=111, start_arg="shop_alice", require_selection=True
        )
        assert resolved is shop_a
        by_name.assert_awaited()
        set_pref.assert_awaited()

        preferred = await sh.get_buyer_shop_config(db, telegram_id=111, require_selection=True)
        assert preferred is shop_b


@pytest.mark.asyncio
async def test_get_buyer_shop_config_requires_selection_when_multi():
    from app.telegram.utils import shop_helpers as sh

    shop_a = SimpleNamespace(admin_id=10, enabled=True)
    shop_b = SimpleNamespace(admin_id=20, enabled=True)
    profile = SimpleNamespace(preferred_shop_admin_id=None)
    db = AsyncMock()

    with (
        patch.object(sh, "get_or_create_telegram_profile", new=AsyncMock(return_value=profile)),
        patch.object(
            sh,
            "list_enabled_shop_configs",
            new=AsyncMock(return_value=[(shop_a, MagicMock()), (shop_b, MagicMock())]),
        ),
        patch.object(sh, "get_enabled_shop_config", new=AsyncMock(return_value=shop_a)),
    ):
        assert await sh.get_buyer_shop_config(db, telegram_id=1, require_selection=True) is None
        assert await sh.get_buyer_shop_config(db, telegram_id=1, require_selection=False) is shop_a


@pytest.mark.asyncio
async def test_record_shop_sale_idempotent():
    from app.db.crud.shop_revenue_ledger import record_shop_sale

    existing = SimpleNamespace(id=1, order_id=42)
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = existing
    db.execute = AsyncMock(return_value=result)

    row = await record_shop_sale(
        db,
        admin_id=1,
        order_id=42,
        amount_toman=1000,
        payment_method="zarinpal",
    )
    assert row is existing
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_list_orders_payment_method_online_filter():
    from app.db.crud import shop as shop_crud
    from app.db.models import ShopOrderStatus

    db = AsyncMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(side_effect=[count_result, list_result])

    orders, total = await shop_crud.list_orders_for_admin(
        db,
        admin_id=1,
        payment_method="online",
        payment_paid=True,
        status=ShopOrderStatus.approved,
    )
    assert orders == []
    assert total == 0
    assert db.execute.await_count == 2
