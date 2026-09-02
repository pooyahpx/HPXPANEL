from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import Response

from app.observability.prometheus import render_metrics
from config import observability_settings

router = APIRouter(tags=["Metrics"], include_in_schema=False)


@router.get("/metrics")
async def prometheus_metrics(authorization: str | None = Header(default=None)):
    if observability_settings.metrics_token:
        expected = f"Bearer {observability_settings.metrics_token}"
        if authorization != expected:
            raise HTTPException(status_code=401, detail="Unauthorized")
    payload, content_type = render_metrics()
    return Response(content=payload, media_type=content_type)
