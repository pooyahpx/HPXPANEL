from datetime import datetime as dt
from enum import Enum

from pydantic import BaseModel, Field

from app.models.system import SystemResourceStats, SystemUsersStats, WorkersHealth


class ProtocolHealthStatus(str, Enum):
    healthy = "healthy"
    degraded = "degraded"
    down = "down"
    unknown = "unknown"


class ProtocolHealth(BaseModel):
    protocol: str
    status: ProtocolHealthStatus = ProtocolHealthStatus.unknown
    latency_ms: int | None = None
    detail: str = ""


class NodeObservabilityCard(BaseModel):
    node_id: int
    name: str
    address: str
    status: str
    cpu_usage: float | None = None
    mem_usage_percent: float | None = None
    incoming_mbps: float | None = None
    outgoing_mbps: float | None = None
    uptime_seconds: int | None = None
    users_total: int = 0
    users_online: int = 0
    protocols: list[ProtocolHealth] = Field(default_factory=list)
    packet_loss_percent: float | None = None
    latency_ms: float | None = None


class MasterObservabilityCard(BaseModel):
    resources: SystemResourceStats
    users: SystemUsersStats
    protocols: list[ProtocolHealth] = Field(default_factory=list)


class AlertEventStatus(str, Enum):
    open = "open"
    acked = "acked"
    resolved = "resolved"


class ObservabilityAlertEventResponse(BaseModel):
    id: int
    scope: str
    node_id: int | None = None
    node_name: str | None = None
    metric: str
    value: float
    threshold: float
    message: str
    status: AlertEventStatus = AlertEventStatus.open
    acked_at: dt | None = None
    acked_by: str | None = None
    resolved_at: dt | None = None
    resolved_by: str | None = None
    note: str | None = None
    created_at: dt


class ObservabilityAlertEventUpdate(BaseModel):
    status: AlertEventStatus
    note: str | None = Field(default=None, max_length=500)


class ObservabilitySummaryResponse(BaseModel):
    generated_at: dt
    master: MasterObservabilityCard | None = None
    nodes: list[NodeObservabilityCard] = Field(default_factory=list)
    workers: WorkersHealth | None = None
    recent_alerts: list[ObservabilityAlertEventResponse] = Field(default_factory=list)
    node_stats_recording_enabled: bool = False


class SystemStatsHistoryPoint(BaseModel):
    period_start: dt
    cpu_usage_percentage: float
    mem_usage_percentage: float
    incoming_mbps: float
    outgoing_mbps: float


class SystemStatsHistoryResponse(BaseModel):
    scope: str
    node_id: int | None = None
    stats: list[SystemStatsHistoryPoint] = Field(default_factory=list)
