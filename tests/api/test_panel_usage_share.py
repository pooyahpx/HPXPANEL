"""Tests for the dashboard "most used configs" (per-node traffic share) helpers."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.db.crud.user import get_panel_usage_by_node
from app.db.models import Admin, Node, NodeUserUsage, User
from app.models.proxy import ProxyTable
from app.utils.usage_share import build_config_usage_share
from tests.api import TestSession, client


def _make_node(name: str) -> Node:
    return Node(
        name=name,
        address="127.0.0.1",
        port=8080,
        api_port=62051,
        server_ca="ca",
        api_key="key",
        core_config_id=None,
    )


class TestBuildConfigUsageShare:
    def test_ranks_and_percentages(self):
        result = build_config_usage_share([(1, 300), (2, 100), (None, 100), (3, 0)], {1: "Alpha", 2: "Beta"})
        assert result.total_bytes == 500
        assert [item.name for item in result.items] == ["Alpha", "Beta", "Panel"]
        assert [item.percent for item in result.items] == [60.0, 20.0, 20.0]

    def test_unknown_node_and_empty(self):
        result = build_config_usage_share([(9, 10)], {})
        assert result.items[0].name == "Node #9"
        assert build_config_usage_share([], {}).items == []


class TestGetPanelUsageByNode:
    @pytest.mark.asyncio
    async def test_groups_by_node_with_admin_filter(self):
        suffix = uuid4().hex[:8]
        async with TestSession() as session:
            admin_a = Admin(username=f"share_a_{suffix}", hashed_password="x", role_id=3)
            admin_b = Admin(username=f"share_b_{suffix}", hashed_password="x", role_id=3)
            session.add_all([admin_a, admin_b])
            await session.flush()
            user_a = User(username=f"ua_{suffix}", admin_id=admin_a.id, proxy_settings=ProxyTable().dict(no_obj=True))
            user_b = User(username=f"ub_{suffix}", admin_id=admin_b.id, proxy_settings=ProxyTable().dict(no_obj=True))
            node_1 = _make_node(f"n1_{suffix}")
            node_2 = _make_node(f"n2_{suffix}")
            session.add_all([user_a, user_b, node_1, node_2])
            await session.flush()

            inside = datetime(2031, 5, 10, 12, 0, tzinfo=UTC)
            outside = datetime(2031, 6, 10, 12, 0, tzinfo=UTC)
            session.add_all(
                [
                    NodeUserUsage(created_at=inside, user_id=user_a.id, node_id=node_1.id, used_traffic=100),
                    NodeUserUsage(created_at=inside, user_id=user_a.id, node_id=node_2.id, used_traffic=700),
                    NodeUserUsage(created_at=inside, user_id=user_b.id, node_id=node_1.id, used_traffic=50),
                    NodeUserUsage(created_at=outside, user_id=user_a.id, node_id=node_1.id, used_traffic=9999),
                ]
            )
            await session.commit()

            start = datetime(2031, 5, 1, tzinfo=UTC)
            end = datetime(2031, 6, 1, tzinfo=UTC)

            rows_all = dict(await get_panel_usage_by_node(session, start, end))
            assert rows_all[node_1.id] == 150
            assert rows_all[node_2.id] == 700

            rows = await get_panel_usage_by_node(session, start, end, admins=[admin_a.username])
            assert rows == [(node_2.id, 700), (node_1.id, 100)]

            rows_b = await get_panel_usage_by_node(session, start, end, admins=[admin_b.username])
            assert rows_b == [(node_1.id, 50)]


def test_panel_usage_share_endpoint(access_token):
    response = client.get("/api/users/usage/share", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    body = response.json()
    assert set(body) >= {"total_bytes", "items", "start", "end"}
    assert isinstance(body["items"], list)

    filtered = client.get(
        "/api/users/usage/share",
        params={"admin": ["nobody-here"]},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert filtered.status_code == 200
    assert filtered.json()["total_bytes"] == 0

