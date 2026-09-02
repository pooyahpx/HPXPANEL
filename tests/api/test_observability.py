from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from app.models.observability import ObservabilitySummaryResponse


def test_observability_summary_endpoint(client, access_token):
    fake_summary = ObservabilitySummaryResponse(
        generated_at=datetime.now(UTC),
        nodes=[],
        node_stats_recording_enabled=False,
    )
    with patch("app.routers.observability.observability_operator.get_summary", new=AsyncMock(return_value=fake_summary)):
        response = client.get(
            "/api/observability/summary",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    assert response.status_code == 200
    assert response.json()["nodes"] == []
