"""CRUD workflow for observability alert acknowledge/resolve."""

from __future__ import annotations

import pytest

from app.db.crud.observability import (
    get_alert_event,
    list_alert_events,
    record_alert_event,
    update_alert_event_status,
)
from app.models.observability import AlertEventStatus
from tests.api import GetTestDB


@pytest.mark.asyncio
async def test_alert_event_record_list_ack_resolve():
    async with GetTestDB() as db:
        event = await record_alert_event(
            db,
            scope="master",
            metric="cpu",
            value=95.5,
            threshold=90.0,
            message="Master CPU 95.5% above 90%",
        )
        assert event.id is not None
        assert event.status == AlertEventStatus.open.value
        assert event.acked_at is None
        assert event.resolved_at is None

        listed = await list_alert_events(db, status=AlertEventStatus.open, limit=50)
        assert any(item.id == event.id for item in listed)
        match = next(item for item in listed if item.id == event.id)
        assert match.status == AlertEventStatus.open
        assert match.message == "Master CPU 95.5% above 90%"

        acked = await update_alert_event_status(
            db,
            event.id,
            status=AlertEventStatus.acked,
            note=None,
            actor_username="testadmin",
        )
        assert acked is not None
        assert acked.status == AlertEventStatus.acked.value
        assert acked.acked_by == "testadmin"
        assert acked.acked_at is not None
        assert acked.resolved_at is None

        open_after_ack = await list_alert_events(db, status=AlertEventStatus.open, limit=50)
        assert all(item.id != event.id for item in open_after_ack)

        acked_listed = await list_alert_events(db, status=AlertEventStatus.acked, limit=50)
        assert any(item.id == event.id for item in acked_listed)

        resolved = await update_alert_event_status(
            db,
            event.id,
            status=AlertEventStatus.resolved,
            note="cleared after scale-out",
            actor_username="testadmin",
        )
        assert resolved is not None
        assert resolved.status == AlertEventStatus.resolved.value
        assert resolved.resolved_by == "testadmin"
        assert resolved.resolved_at is not None
        assert resolved.note == "cleared after scale-out"

        fetched = await get_alert_event(db, event.id)
        assert fetched is not None
        assert fetched.status == AlertEventStatus.resolved.value
        assert fetched.acked_by == "testadmin"
        assert fetched.resolved_by == "testadmin"


@pytest.mark.asyncio
async def test_alert_event_resolve_from_open_auto_acks():
    async with GetTestDB() as db:
        event = await record_alert_event(
            db,
            scope="node",
            metric="mem",
            value=92.0,
            threshold=85.0,
            message="Node memory high",
            node_id=None,
        )

        resolved = await update_alert_event_status(
            db,
            event.id,
            status=AlertEventStatus.resolved,
            note=None,
            actor_username="ops",
        )
        assert resolved is not None
        assert resolved.status == AlertEventStatus.resolved.value
        assert resolved.resolved_by == "ops"
        assert resolved.acked_by == "ops"
        assert resolved.acked_at is not None
        assert resolved.resolved_at is not None
