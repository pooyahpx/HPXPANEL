"""Self-service HWID endpoints on the public subscription portal."""

from __future__ import annotations

import asyncio

from fastapi import status

from app.db.crud.hwid import register_user_hwid, reset_user_hwids
from tests.api import TestSession, client
from tests.api.helpers import create_user, delete_user
from tests.api.test_hwid import _set_user_hwid_limit


def test_subscription_portal_hwid_list_delete_reset(access_token):
    user = create_user(access_token, payload={"hwid_limit": 3})
    sub = user["subscription_url"].rstrip("/")

    try:
        asyncio.run(_set_user_hwid_limit(user["id"], 3))

        async def _seed():
            async with TestSession() as session:
                await reset_user_hwids(session, user["id"])
                await register_user_hwid(session, user["id"], "portal-device-1", "Android", "14", "Pixel")
                await register_user_hwid(session, user["id"], "portal-device-2", "iOS", "17", "iPhone")

        asyncio.run(_seed())

        listed = client.get(f"{sub}/hwids")
        assert listed.status_code == status.HTTP_200_OK, listed.text
        body = listed.json()
        assert body["count"] == 2
        hwids = {item["hwid"] for item in body["hwids"]}
        assert hwids == {"portal-device-1", "portal-device-2"}

        deleted = client.delete(f"{sub}/hwids/portal-device-1")
        assert deleted.status_code == status.HTTP_204_NO_CONTENT, deleted.text

        listed_after = client.get(f"{sub}/hwids")
        assert listed_after.status_code == status.HTTP_200_OK
        assert listed_after.json()["count"] == 1
        assert listed_after.json()["hwids"][0]["hwid"] == "portal-device-2"

        reset = client.post(f"{sub}/hwids/reset")
        assert reset.status_code == status.HTTP_200_OK, reset.text
        assert reset.json()["count"] == 1
        assert client.get(f"{sub}/hwids").json()["count"] == 0
    finally:
        asyncio.run(_set_user_hwid_limit(user["id"], None))
        delete_user(access_token, user["username"])


def test_subscription_portal_hwid_disabled_returns_empty(access_token):
    user = create_user(access_token, payload={"hwid_limit": 0})
    sub = user["subscription_url"].rstrip("/")

    try:
        asyncio.run(_set_user_hwid_limit(user["id"], 0))
        listed = client.get(f"{sub}/hwids")
        assert listed.status_code == status.HTTP_200_OK, listed.text
        assert listed.json() == {"hwids": [], "count": 0}

        deleted = client.delete(f"{sub}/hwids/anything")
        assert deleted.status_code == status.HTTP_403_FORBIDDEN
    finally:
        delete_user(access_token, user["username"])


def test_subscription_portal_html_includes_support_and_devices(access_token):
    user = create_user(access_token, payload={"hwid_limit": 2})
    sub = user["subscription_url"].rstrip("/")

    try:
        asyncio.run(_set_user_hwid_limit(user["id"], 2))
        page = client.get(sub, headers={"Accept": "text/html"})
        assert page.status_code == status.HTTP_200_OK, page.text
        assert "text/html" in page.headers.get("content-type", "")
        assert "Devices" in page.text
        assert "https://t.me/" in page.text
        assert "Support" in page.text
    finally:
        delete_user(access_token, user["username"])
