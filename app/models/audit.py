from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AuditLogResponse(BaseModel):
    id: int
    actor_id: int | None = None
    actor_username: str | None = None
    source_ip: str | None = None
    action: str
    resource: str
    resource_id: str | None = None
    before: dict[str, Any] | list[Any] | None = None
    after: dict[str, Any] | list[Any] | None = None
    result: str
    detail: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogsResponse(BaseModel):
    logs: list[AuditLogResponse]
    total: int
    offset: int
    limit: int


class AuditLogQuery(BaseModel):
    search: str | None = Field(default=None, max_length=256)
    actor: str | None = Field(default=None, max_length=128)
    action: str | None = Field(default=None, max_length=64)
    resource: str | None = Field(default=None, max_length=64)
    result: Literal["success", "failure"] | None = None
    start: datetime | None = None
    end: datetime | None = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=200)

    @field_validator("start", "end")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("date filters must include a timezone")
        return value

    @field_validator("end")
    @classmethod
    def validate_range(cls, value: datetime | None, info) -> datetime | None:
        start = info.data.get("start")
        if value is not None and start is not None and value < start:
            raise ValueError("end must be greater than or equal to start")
        return value
