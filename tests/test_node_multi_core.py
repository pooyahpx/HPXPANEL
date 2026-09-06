"""Multi-core per node bindings and connect loop."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models import CoreType, NodeStatus
from app.models.node import NodeModify
from app.operation import OperatorType
from app.operation.node import NodeOperation


def test_node_modify_syncs_core_config_ids():
    modify = NodeModify(core_config_ids=[5, 6])
    assert modify.core_config_ids == [5, 6]
    assert modify.core_config_id == 5


def test_node_modify_partial_without_cores():
    modify = NodeModify(name="only-name")
    assert modify.core_config_ids is None
    assert modify.core_config_id is None


def test_node_modify_rejects_empty_core_list():
    with pytest.raises(Exception):
        NodeModify(core_config_ids=[])


@pytest.mark.asyncio
async def test_connect_node_multi_starts_each_core(monkeypatch):
    starts: list = []

    class FakeInfo:
        core_version = "1.0.0"
        node_version = "2.0.0"

    class FakeNode:
        async def start(self, **kwargs):
            starts.append(kwargs["backend_type"])
            return FakeInfo()

    async def fake_get_node(_id):
        return FakeNode()

    monkeypatch.setattr("app.operation.node.node_manager.get_node", fake_get_node)
    monkeypatch.setattr(
        "app.operation.node._backend_type_for_core",
        lambda t: f"BT_{t}",
    )

    db_node = SimpleNamespace(id=7, name="n1", keep_alive=10, status=NodeStatus.connecting)
    core_xray = SimpleNamespace(type=CoreType.xray, exclude_inbound_tags=[], to_str=lambda: "{}")
    core_wg = SimpleNamespace(type=CoreType.wg, exclude_inbound_tags=[], to_str=lambda: "{}")

    result = await NodeOperation.connect_node_multi(
        db_node,
        [(core_xray, []), (core_wg, [])],
    )

    assert result is not None
    assert result["status"] == NodeStatus.connected
    assert len(starts) == 2
    assert "xray" in str(starts[0]).lower()
    assert "wg" in str(starts[1]).lower()


@pytest.mark.asyncio
async def test_validate_rejects_two_xray_cores():
    op = NodeOperation(operator_type=OperatorType.API)

    async def fake_get_core(_db, core_id):
        return SimpleNamespace(id=core_id, type=CoreType.xray)

    op.get_validated_core_config = fake_get_core  # type: ignore[method-assign]
    op.raise_error = AsyncMock(side_effect=RuntimeError("boom"))  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="boom"):
        await op._validate_node_core_ids(MagicMock(), [1, 2])
    op.raise_error.assert_awaited()
