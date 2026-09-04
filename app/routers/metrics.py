import secrets

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import Response

from app.observability.prometheus import render_metrics
from config import observability_settings

router = APIRouter(tags=["Metrics"], include_in_schema=False)


@router.get("/metrics")
async def prometheus_metrics(authorization: str | None = Header(default=None)):
    metrics_token = observability_settings.metrics_token
    if metrics_token:
        scheme, _, credentials = (authorization or "").partition(" ")
        if scheme.lower() != "bearer" or not secrets.compare_digest(credentials, metrics_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing metrics bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    elif not observability_settings.metrics_allow_unauthenticated:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Metrics authentication is not configured. Set OBSERVABILITY_METRICS_TOKEN "
                "or explicitly enable OBSERVABILITY_METRICS_ALLOW_UNAUTHENTICATED."
            ),
        )
    payload, content_type = render_metrics()
    return Response(content=payload, media_type=content_type)
