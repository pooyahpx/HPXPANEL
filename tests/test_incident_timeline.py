"""Incident timeline + SOAR actions for observability alerts."""

from __future__ import annotations

import pytest

from app.db.crud.observability import (
    add_alert_note,
    get_alert_event_detail,
    list_alert_timeline_events,
    record_alert_event,
    update_alert_event_status,
    update_alert_severity,
)
from app.models.observability import AlertEventStatus, AlertTimelineEventType
from tests.api import GetTestDB


@pytest.mark.asyncio
async def test_alert_timeline_created_ack_note_severity():
    async with GetTestDB() as db:
        event = await record_alert_event(
            db,
            scope="master",
            metric="cpu",
            value=97.0,
            threshold=90.0,
            message="CPU spike",
            severity="critical",
        )
        timeline = await list_alert_timeline_events(db, event.id)
        assert timeline
        assert timeline[0].event_type == AlertTimelineEventType.created

        await update_alert_event_status(
            db,
            event.id,
            status=AlertEventStatus.acked,
            note=None,
            actor_username="ops",
        )
        await add_alert_note(db, event.id, message="watching", actor_username="ops")
        await update_alert_severity(db, event.id, severity="warning", actor_username="ops")

        detail = await get_alert_event_detail(db, event.id)
        assert detail is not None
        assert detail.severity.value == "warning"
        types = [item.event_type for item in detail.timeline]
        assert AlertTimelineEventType.created in types
        assert AlertTimelineEventType.status_changed in types
        assert AlertTimelineEventType.note_added in types
        assert AlertTimelineEventType.severity_changed in types
