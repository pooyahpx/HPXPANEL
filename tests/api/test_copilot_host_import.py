from __future__ import annotations

import pytest
from fastapi import status

from app.routers.authentication import get_admin as get_auth_admin
from app.services.copilot.tools import execute_tool
from tests.api import GetTestDB, client
from tests.api.helpers import auth_headers, create_core, delete_core, get_inbounds

VLESS_LINK = (
    "vless://0373083d-5359-449f-815d-79f0e881c2bf@example.com:443"
    "?encryption=none&security=tls&sni=sni.example&type=ws&path=/ws#France"
)


@pytest.mark.asyncio
async def test_execute_tool_import_proxy_link_preview_and_create(access_token):
    core = create_core(access_token)
    inbound_tag = "VLESS WebSocket TEST"
    try:
        inbounds = get_inbounds(access_token)
        assert inbound_tag in inbounds

        async with GetTestDB() as db:
            admin = await get_auth_admin(db, access_token)
            assert admin is not None

            preview, action = await execute_tool(
                db,
                admin=admin,
                name="import_proxy_link",
                arguments={"link": VLESS_LINK, "inbound_tag": inbound_tag, "confirm": False},
            )

        assert action == "Previewed proxy link import"
        assert preview.get("ready") is True
        assert preview["host"]["inbound_tag"] == inbound_tag
        assert preview["host"]["remark"] == "France"
        assert "host_id" not in preview

        async with GetTestDB() as db:
            admin = await get_auth_admin(db, access_token)
            assert admin is not None
            created, action = await execute_tool(
                db,
                admin=admin,
                name="import_proxy_link",
                arguments={"link": VLESS_LINK, "inbound_tag": inbound_tag, "confirm": True},
            )

        assert created.get("host_id")
        assert created["host_remark"] == "France"
        assert "Imported host" in (action or "")

        host_id = created["host_id"]
        response = client.get(f"/api/host/{host_id}", headers=auth_headers(access_token))
        assert response.status_code == status.HTTP_200_OK
        host = response.json()
        assert host["remark"] == "France"
        assert host["inbound_tag"] == inbound_tag
        assert "example.com" in host["address"]

        client.delete(f"/api/host/{host_id}", headers=auth_headers(access_token))
    finally:
        delete_core(access_token, core["id"])
