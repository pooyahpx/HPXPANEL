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


def test_shop_plan_crud_and_stats(shop_admin):
    headers = auth_headers(shop_admin["token"])
    created = client.post(
        "/api/shop/plans",
        headers=headers,
        json={
            "name": "Web Plan 30G",
            "data_limit": 30 * 1024**3,
            "expire_days": 30,
            "price_toman": 150000,
        },
    )
    assert created.status_code == status.HTTP_201_CREATED, created.text
    plan = created.json()
    plan_id = plan["id"]
    assert plan["name"] == "Web Plan 30G"
    assert plan["is_active"] is True

    listed = client.get("/api/shop/plans", headers=headers)
    assert listed.status_code == status.HTTP_200_OK
    assert any(item["id"] == plan_id for item in listed.json())

    patched = client.patch(
        f"/api/shop/plans/{plan_id}",
        headers=headers,
        json={"is_active": False, "price_toman": 160000},
    )
    assert patched.status_code == status.HTTP_200_OK, patched.text
    assert patched.json()["is_active"] is False
    assert patched.json()["price_toman"] == 160000

    stats = client.get("/api/shop/stats", headers=headers)
    assert stats.status_code == status.HTTP_200_OK, stats.text
    assert "orders_pending" in stats.json()

    deleted = client.delete(f"/api/shop/plans/{plan_id}", headers=headers)
    assert deleted.status_code == status.HTTP_204_NO_CONTENT, deleted.text


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
