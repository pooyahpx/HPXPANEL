from datetime import datetime as dt
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.db.models import HpxTunnelRole, HpxTunnelStatus


class HpxPortForward(BaseModel):
    external_port: int = Field(ge=1, le=65535)
    internal_ip: str = Field(min_length=7, max_length=45)
    internal_port: int = Field(ge=1, le=65535)


class HpxTunnelBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    role: HpxTunnelRole
    enabled: bool = True
    remote_ip: str | None = Field(default=None, max_length=45)
    server_listen: str = Field(default="0.0.0.0", max_length=45)
    interface: str = Field(default="hpx0", max_length=32)
    local_ip: str = Field(default="10.200.200.2", max_length=45)
    subnet: str = Field(default="10.200.200.0/24", max_length=64)
    mtu: int | None = Field(default=1500, ge=576, le=9000)
    keepalive: int = Field(default=5, ge=1, le=300)
    dscp_mark: int | None = Field(default=None, ge=0, le=63)
    bandwidth_limit: str | None = Field(default=None, max_length=32)
    operating_mode: str | None = Field(default=None, max_length=64)
    port_forwards: list[HpxPortForward] = Field(default_factory=list)
    docker_image: str = Field(default="pooyahpx/hpx-icmp:0.0.3", max_length=128)
    backup_tunnel_id: int | None = Field(default=None, ge=1)
    auto_failover: bool = False
    priority: int = Field(default=0, ge=0, le=100)
    alert_on_down: bool = True
    note: str | None = Field(default=None, max_length=512)

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def validate_role_fields(self):
        if self.role == HpxTunnelRole.iran and not self.remote_ip:
            raise ValueError("remote_ip is required for IRAN (client) tunnels")
        if self.role == HpxTunnelRole.foreign and not self.server_listen:
            raise ValueError("server_listen is required for FOREIGN (server) tunnels")
        return self


class HpxTunnelCreate(HpxTunnelBase):
    password: str = Field(min_length=4, max_length=128)
    start_after_create: bool = True


class HpxTunnelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    enabled: bool | None = None
    password: str | None = Field(default=None, min_length=4, max_length=128)
    remote_ip: str | None = Field(default=None, max_length=45)
    server_listen: str | None = Field(default=None, max_length=45)
    interface: str | None = Field(default=None, max_length=32)
    local_ip: str | None = Field(default=None, max_length=45)
    subnet: str | None = Field(default=None, max_length=64)
    mtu: int | None = Field(default=None, ge=576, le=9000)
    keepalive: int | None = Field(default=None, ge=1, le=300)
    dscp_mark: int | None = Field(default=None, ge=0, le=63)
    bandwidth_limit: str | None = Field(default=None, max_length=32)
    operating_mode: str | None = Field(default=None, max_length=64)
    port_forwards: list[HpxPortForward] | None = None
    docker_image: str | None = Field(default=None, max_length=128)
    backup_tunnel_id: int | None = Field(default=None, ge=1)
    auto_failover: bool | None = None
    priority: int | None = Field(default=None, ge=0, le=100)
    alert_on_down: bool | None = None
    note: str | None = Field(default=None, max_length=512)


class HpxTunnelResponse(HpxTunnelBase):
    id: int
    status: HpxTunnelStatus
    container_name: str
    has_password: bool = True
    agent_claimed: bool = False
    agent_host: str | None = None
    agent_last_seen: dt | None = None
    agent_claimed_at: dt | None = None
    join_token_expires_at: dt | None = None
    last_health_check: dt | None = None
    latency_ms: float | None = None
    packet_loss_pct: float | None = None
    message: str | None = None
    bytes_up: int = 0
    bytes_down: int = 0
    created_at: dt
    last_status_change: dt | None = None


class HpxTunnelsResponse(BaseModel):
    tunnels: list[HpxTunnelResponse]
    total: int


class HpxTunnelsQuery(BaseModel):
    offset: int | None = Field(default=None, ge=0)
    limit: int | None = Field(default=None, ge=1, le=500)
    tunnel_id: int | None = Field(default=None, ge=1)
    name: str | None = None
    role: HpxTunnelRole | None = None
    status: HpxTunnelStatus | None = None


class BulkHpxTunnelSelection(BaseModel):
    ids: Annotated[list[int], Field(min_length=1)]


class RemoveHpxTunnelsResponse(BaseModel):
    tunnels: list[str]
    count: int


class HpxTunnelStatsResponse(BaseModel):
    tunnel_id: int
    status: HpxTunnelStatus
    container_running: bool
    interface_up: bool
    interface_ip: str | None = None
    latency_ms: float | None = None
    packet_loss_pct: float | None = None
    bytes_up: int = 0
    bytes_down: int = 0
    uptime_seconds: int | None = None
    message: str | None = None


class HpxTunnelActionResponse(BaseModel):
    tunnel: HpxTunnelResponse
    message: str | None = None
    join_token: str | None = None
    join_command: str | None = None
    join_expires_at: dt | None = None


class HpxTunnelJoinTokenResponse(BaseModel):
    tunnel_id: int
    join_token: str
    join_command: str
    join_expires_at: dt


class HpxTunnelAgentClaimRequest(BaseModel):
    join_token: str = Field(min_length=16, max_length=128)
    host: str | None = Field(default=None, max_length=255)


class HpxTunnelAgentBootstrap(BaseModel):
    tunnel_id: int
    name: str
    role: HpxTunnelRole
    password: str
    remote_ip: str | None = None
    interface: str
    local_ip: str
    subnet: str
    mtu: int | None = None
    keepalive: int
    dscp_mark: int | None = None
    port_forwards: list[HpxPortForward] = Field(default_factory=list)
    docker_image: str
    container_name: str
    agent_key: str
    config_hash: str
    desired_status: HpxTunnelStatus
    agent_command: str | None = None


class HpxTunnelAgentConfigResponse(BaseModel):
    tunnel_id: int
    name: str
    role: HpxTunnelRole
    password: str
    remote_ip: str | None = None
    interface: str
    local_ip: str
    subnet: str
    mtu: int | None = None
    keepalive: int
    dscp_mark: int | None = None
    port_forwards: list[HpxPortForward] = Field(default_factory=list)
    docker_image: str
    container_name: str
    config_hash: str
    desired_status: HpxTunnelStatus
    agent_command: str | None = None
    enabled: bool = True


class HpxTunnelAgentHeartbeatRequest(BaseModel):
    status: HpxTunnelStatus
    host: str | None = Field(default=None, max_length=255)
    latency_ms: float | None = None
    packet_loss_pct: float | None = None
    bytes_up: int = 0
    bytes_down: int = 0
    message: str | None = Field(default=None, max_length=1024)
    container_running: bool = False
    interface_up: bool = False


class HpxTunnelAgentAckRequest(BaseModel):
    command: str = Field(min_length=1, max_length=16)
    status: HpxTunnelStatus | None = None
    message: str | None = Field(default=None, max_length=1024)