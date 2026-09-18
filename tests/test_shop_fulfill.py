import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.db.models import ShopOrderStatus
from app.operation.shop import ShopOperation
from app.operation import OperatorType


@pytest.mark.asyncio
async def test_fulfill_paid_order_accepts_awaiting_payment():
    op = ShopOperation(OperatorType.API)
    order = SimpleNamespace(
        id=99,
        admin_id=1,
        status=ShopOrderStatus.awaiting_payment,
        payment_paid=False,
    )
    db = AsyncMock()
    admin_details = MagicMock()

    with (
        patch("app.operation.shop.get_shop_order", new=AsyncMock(side_effect=[order, order, order])),
        patch("app.operation.shop.update_shop_order_payment", new=AsyncMock()) as upd_pay,
        patch("app.operation.shop.update_order_status", new=AsyncMock()) as upd_status,
        patch("app.operation.shop.get_admin_by_id", new=AsyncMock(return_value=MagicMock())),
        patch("app.operation.shop.build_admin_details", return_value=admin_details),
        patch.object(op, "approve_order", new=AsyncMock(return_value=MagicMock(username="u1"))) as approve,
    ):
        result = await op.fulfill_paid_order(db, 99)

    assert result is not None
    upd_pay.assert_awaited()
    upd_status.assert_awaited()
    assert upd_status.await_args.args[2] == ShopOrderStatus.pending
    approve.assert_awaited()


@pytest.mark.asyncio
async def test_fulfill_paid_order_skips_expired():
    op = ShopOperation(OperatorType.API)
    order = SimpleNamespace(id=5, admin_id=1, status=ShopOrderStatus.expired, payment_paid=False)
    with patch("app.operation.shop.get_shop_order", new=AsyncMock(return_value=order)):
        assert await op.fulfill_paid_order(AsyncMock(), 5) is None
