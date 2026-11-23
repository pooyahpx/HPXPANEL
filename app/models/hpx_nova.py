from datetime import datetime as dt
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HpxNovaStatus(StrEnum):
    pending_claim = "pending_claim"
    running = "running"
    stopped = "stopped"
    starting = "starting"
    stopping = "stopping"
    error = "error"
    unhealthy = "unhealthy"
    partial = "partial"


class HpxNovaCarrier(StrEnum):
    wss = "wss"
    ws = "ws"
    quic = "quic"
    tcp = "tcp"
    tls = "tls"


class HpxNovaCreate(BaseModel):
    name: str = Field(min_length=2, max_length=40)
    iran_public_ip: str = Field(min_length=3, max_length=45)
    abroad_public_ip: str = Field(min_length=3, max_length=45)
    carrier: HpxNovaCarrier = HpxNovaCarrier.wss
    lanes: int = Field(default=4, ge=1, le=16)
    resume: bool = True
    tunnel_port: int = Field(default=8443, ge=1, le=65535)
    sni: str | None = Field(default="www.cloudflare.com", max_length=255)
    ws_path: str | None = Field(default="/live", max_length=128)
    port_forwards: list[str] = Field(default_factory=list)
    proxy_listen: str | None = Field(default="127.0.0.1:1080", max_length=64)
    note: str | None = Field(default=None, max_length=512)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name is required")
        return cleaned


class HpxNovaUpdate(BaseModel):
    note: str | None = Field(default=None, max_length=512)
    enabled: bool | None = None
    port_forwards: list[str] | None = None
    proxy_listen: str | None = Field(default=None, max_length=64)
    sni: str | None = Field(default=None, max_length=255)
    lanes: int | None = Field(default=None, ge=1, le=16)


class HpxNovaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: HpxNovaStatus
    enabled: bool
    engine: str
    carrier: str
    lanes: int
    resume: bool
    iran_public_ip: str
    abroad_public_ip: str
    tunnel_port: int
    sni: str | None = None
    ws_path: str | None = None
    port_forwards: list[str] | None = None
    proxy_listen: str | None = None
    note: str | None = None
    iran_claimed: bool = False
    abroad_claimed: bool = False
    iran_agent_online: bool = False
    abroad_agent_online: bool = False
    iran_agent_host: str | None = None
    abroad_agent_host: str | None = None
    iran_agent_last_seen: dt | None = None
    abroad_agent_last_seen: dt | None = None
    latency_ms: float | None = None
    message: str | None = None
    created_at: dt | None = None
    last_status_change: dt | None = None


class HpxNovasResponse(BaseModel):
    novas: list[HpxNovaResponse]
    total: int


class HpxNovaActionResponse(BaseModel):
    detail: str
    nova: HpxNovaResponse | None = None
    iran_join_token: str | None = None
    abroad_join_token: str | None = None
    iran_join_command: str | None = None
    iran_join_command_alt: str | None = None
    abroad_join_command: str | None = None
    abroad_join_command_alt: str | None = None
    join_expires_at: dt | None = None


class HpxNovaAgentClaimRequest(BaseModel):
    join_token: str = Field(min_length=16, max_length=256)
    side: str = Field(pattern="^(iran|abroad)$")
    host: str | None = Field(default=None, max_length=255)


class HpxNovaAgentBootstrap(BaseModel):
    nova_id: int
    side: str
    agent_key: str
    panel_url: str
    engine_version: str
    config_toml: str
    command: str | None = "start"


class HpxNovaAgentConfigResponse(BaseModel):
    nova_id: int
    side: str
    config_toml: str
    command: str | None = None
    engine_version: str
    enabled: bool


class HpxNovaAgentHeartbeatRequest(BaseModel):
    host: str | None = None
    latency_ms: float | None = None
    engine_version: str | None = None
    status: str | None = None
    message: str | None = None


class HpxNovaAgentAckRequest(BaseModel):
    command: str = Field(min_length=1, max_length=64)
