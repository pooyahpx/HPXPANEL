"""API tests for the web shop admin surface."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import status
from sqlalchemy import select

from app.db.models import Admin, ShopOrder, ShopOrderStatus
from app.models.admin import hash_password
from tests.api import TestSession, client
from tests.api.helpers import auth_headers, strong_password, unique_name


@pytest.fixture
def shop_admin():
    username = unique_name("shopowner")
    password = strong_password("ShopOwner")

    async def _create():
        async with TestSession() as session:
            db_admin = Admin(username=username, hashed_password=await hash_password(password), role_id=1)
            session.add(db_admin)
            await session.commit()
            await session.refresh(db_admin)
            return db_admin.id

    admin_id = asyncio.run(_create())
    login = client.post(
        "/api/admin/token",
        data={"username": username, "password": password, "grant_type": "password"},
    )
    assert login.status_code == status.HTTP_200_OK, login.text
    token = login.json()["access_token"]

    yield {"id": admin_id, "username": username, "password": password, "token": token}

    async def _cleanup():
        async with TestSession() as session:
            db_admin = (await session.execute(select(Admin).where(Admin.username == username))).scalar_one_or_none()
            if db_admin is not None:
                await session.delete(db_admin)
                await session.commit()

    asyncio.run(_cleanup())


def test_shop_config_get_and_update(shop_admin):
    headers = auth_headers(shop_admin["token"])
    got = client.get("/api/shop/config", headers=headers)
    assert got.status_code == status.HTTP_200_OK, got.text
    body = got.json()
    assert body["enabled"] in (True, False)
    assert "cards" in body

    updated = client.put(
        "/api/shop/config",
        headers=headers,
        json={
            "enabled": True,
            "welcome_note": "hello shop",
            "card_note": "pay here",
            "cards": [{"number": "6037991234567890", "holder": "HPX"}],
        },
    )
    assert updated.status_code == status.HTTP_200_OK, updated.text
    data = updated.json()
    assert data["enabled"] is True
    assert data["welcome_note"] == "hello shop"
    assert data["cards"][0]["number"] == "6037991234567890"
    assert data["card_number"] == "6037991234567890"


def test_shop_payment_gateway_config(shop_admin):
    headers = auth_headers(shop_admin["token"])
    updated = client.put(
        "/api/shop/config",
        headers=headers,
        json={
            "pay_card_enabled": True,
            "pay_zarinpal_enabled": True,
            "pay_zarinpal_merchant_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "pay_zarinpal_sandbox": True,
            "pay_callback_base_url": "https://panel.example.com",
            "pay_stripe_enabled": False,
            "pay_paypal_enabled": False,
            "pay_idpay_enabled": False,
            "pay_nowpayments_enabled": False,
        },
    )
    assert updated.status_code == status.HTTP_200_OK, updated.text
    data = updated.json()
    assert data["pay_card_enabled"] is True
    assert data["pay_zarinpal_enabled"] is True
    assert data["pay_zarinpal_merchant_id"] == "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    assert data["pay_callback_base_url"] == "https://panel.example.com"
    assert "zarinpal" in data["enabled_gateways"]
    assert "card" in data["enabled_gateways"]


def test_shop_plan_crud_and_stats(shop_admin):
    headers = auth_headers(shop_admin["token"])
    from tests.api.helpers import create_core, create_group, delete_core

    core = create_core(shop_admin["token"])
    try:
        group = create_group(shop_admin["token"])
        created = client.post(
            "/api/shop/plans",
            headers=headers,
            json={
                "name": "Web Plan 30G",
                "data_limit": 30 * 1024**3,
                "expire_days": 30,
                "price_toman": 150000,
                "group_ids": [group["id"]],
            },
        )
        assert created.status_code == status.HTTP_201_CREATED, created.text
        plan = created.json()
        plan_id = plan["id"]
        assert plan["name"] == "Web Plan 30G"
        assert plan["is_active"] is True
        assert plan["group_ids"] == [group["id"]]

        listed = client.get("/api/shop/plans", headers=headers)
        assert listed.status_code == status.HTTP_200_OK
        assert any(item["id"] == plan_id for item in listed.json())

        patched = client.patch(
            f"/api/shop/plans/{plan_id}",
            headers=headers,
            json={"is_active": False, "price_toman": 160000, "group_ids": [group["id"]]},
        )
        assert patched.status_code == status.HTTP_200_OK, patched.text
        assert patched.json()["is_active"] is False
        assert patched.json()["price_toman"] == 160000
        assert patched.json()["group_ids"] == [group["id"]]

        empty_groups = client.post(
            "/api/shop/plans",
            headers=headers,
            json={
                "name": "No Groups Plan",
                "data_limit": 1024**3,
                "expire_days": 7,
                "price_toman": 1000,
                "group_ids": [],
            },
        )
        assert empty_groups.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, empty_groups.text

        stats = client.get("/api/shop/stats", headers=headers)
        assert stats.status_code == status.HTTP_200_OK, stats.text
        assert "orders_pending" in stats.json()

        deleted = client.delete(f"/api/shop/plans/{plan_id}", headers=headers)
        assert deleted.status_code == status.HTTP_204_NO_CONTENT, deleted.text
    finally:
        delete_core(shop_admin["token"], core["id"])


def test_shop_order_approve_and_reject(shop_admin):
    headers = auth_headers(shop_admin["token"])
    from tests.api.helpers import create_core, create_group, delete_core

    core = create_core(shop_admin["token"])
    try:
        group = create_group(shop_admin["token"])
        plan = client.post(
            "/api/shop/plans",
            headers=headers,
            json={
                "name": "Approve Plan",
                "data_limit": 1024**3,
                "expire_days": 7,
                "price_toman": 50000,
                "group_ids": [group["id"]],
            },
        ).json()

        async def _seed_orders():
            from app.db.crud.shop import create_shop_order

            async with TestSession() as session:
                pending_approve = await create_shop_order(
                    session,
                    plan_id=plan["id"],
                    admin_id=shop_admin["id"],
                    buyer_telegram_id=900001,
                    buyer_username="buyer_ok",
                    receipt_file_id="file-approve",
                )
                pending_reject = await create_shop_order(
                    session,
                    plan_id=plan["id"],
                    admin_id=shop_admin["id"],
                    buyer_telegram_id=900002,
                    buyer_username="buyer_no",
                    receipt_file_id="file-reject",
                )
                return pending_approve.id, pending_reject.id

        approve_id, reject_id = asyncio.run(_seed_orders())

        listed = client.get("/api/shop/orders", headers=headers, params={"status": "pending"})
        assert listed.status_code == status.HTTP_200_OK, listed.text
        ids = {item["id"] for item in listed.json()["orders"]}
        assert approve_id in ids
        assert reject_id in ids

        approved = client.post(f"/api/shop/orders/{approve_id}/approve", headers=headers)
        assert approved.status_code == status.HTTP_200_OK, approved.text
        assert approved.json()["username"].startswith("tg900001_")
        assert approved.json()["order"]["status"] == "approved"

        rejected = client.post(f"/api/shop/orders/{reject_id}/reject", headers=headers, json={"note": "bad receipt"})
        assert rejected.status_code == status.HTTP_200_OK, rejected.text
        assert rejected.json()["status"] == "rejected"
        assert rejected.json()["note"] == "bad receipt"

        async def _assert_db():
            async with TestSession() as session:
                approve_order = (await session.execute(select(ShopOrder).where(ShopOrder.id == approve_id))).scalar_one()
                reject_order = (await session.execute(select(ShopOrder).where(ShopOrder.id == reject_id))).scalar_one()
                assert approve_order.status == ShopOrderStatus.approved
                assert approve_order.created_user_id is not None
                assert reject_order.status == ShopOrderStatus.rejected

        asyncio.run(_assert_db())
    finally:
        delete_core(shop_admin["token"], core["id"])


def test_shop_custom_config_requires_groups(shop_admin):
    headers = auth_headers(shop_admin["token"])
    from tests.api.helpers import create_core, create_group, delete_core

    core = create_core(shop_admin["token"])
    try:
        blocked = client.put(
            "/api/shop/config",
            headers=headers,
            json={"custom_enabled": True, "custom_group_ids": []},
        )
        assert blocked.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY), blocked.text

        group = create_group(shop_admin["token"])
        ok = client.put(
            "/api/shop/config",
            headers=headers,
            json={
                "custom_enabled": True,
                "custom_price_per_gb": 5000,
                "custom_price_per_day": 2000,
                "custom_price_per_ip": 10000,
                "custom_min_gb": 1,
                "custom_max_gb": 100,
                "custom_min_days": 1,
                "custom_max_days": 90,
                "custom_base_ip": 1,
                "custom_group_ids": [group["id"]],
            },
        )
        assert ok.status_code == status.HTTP_200_OK, ok.text
        body = ok.json()
        assert body["custom_enabled"] is True
        assert body["custom_group_ids"] == [group["id"]]
        assert body["custom_price_per_gb"] == 5000
    finally:
        delete_core(shop_admin["token"], core["id"])


def test_shop_custom_order_approve_with_requested_username(shop_admin):
    headers = auth_headers(shop_admin["token"])
    from tests.api.helpers import create_core, create_group, delete_core

    core = create_core(shop_admin["token"])
    try:
        group = create_group(shop_admin["token"])
        client.put(
            "/api/shop/config",
            headers=headers,
            json={
                "enabled": True,
                "custom_enabled": True,
                "custom_group_ids": [group["id"]],
                "custom_price_per_gb": 1000,
                "custom_price_per_day": 100,
                "custom_price_per_ip": 500,
                "custom_base_ip": 1,
            },
        )

        async def _seed():
            from app.db.crud.shop import create_shop_order

            async with TestSession() as session:
                order = await create_shop_order(
                    session,
                    plan_id=None,
                    admin_id=shop_admin["id"],
                    buyer_telegram_id=910001,
                    buyer_username="custom_buyer",
                    receipt_file_id="file-custom",
                    requested_username="mycustomuser",
                    custom_data_gb=5,
                    custom_expire_days=10,
                    custom_ip_limit=2,
                    quoted_price_toman=6500,
                    is_custom=True,
                )
                return order.id

        order_id = asyncio.run(_seed())
        approved = client.post(f"/api/shop/orders/{order_id}/approve", headers=headers)
        assert approved.status_code == status.HTTP_200_OK, approved.text
        assert approved.json()["username"] == "mycustomuser"
        assert approved.json()["order"]["is_custom"] is True
        assert approved.json()["order"]["custom_data_gb"] == 5
    finally:
        delete_core(shop_admin["token"], core["id"])
