from datetime import datetime as dt
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

PulseGoal = Literal["stealth", "balanced", "speed"]
PulseSide = Literal["iran", "abroad"]
PulseEngine = Literal["hpx", "native"]
PulseStatus = Literal[
    "pending_claim",
    "running",
    "starting",
    "stopped",
    "stopping",
    "error",
    "unhealthy",
    "partial",
]


class PulseAdviseRequest(BaseModel):
    cpu_cores: int = Field(default=1, ge=1, le=128)
    ram_mb: int = Field(default=1024, ge=256, le=1_048_576)
    udp_reachable: bool | None = None
    packet_loss_pct: float | None = Field(default=None, ge=0, le=100)
    goal: PulseGoal = "balanced"


class PulseProfileOption(BaseModel):
    profile_id: str
    title: str
    title_fa: str
    tunnel_mode: str
    carrier: str | None = None
    preset: str
    score: int = Field(ge=0, le=100)
    reasons: list[str]
    reasons_fa: list[str]
    warnings: list[str] = Field(default_factory=list)


class PulseRealityFrontAdvice(BaseModel):
    domain_on_iran: bool = True
    sni: str | None = None
    dest: str = "play.google.com:443"
    checklist: list[str]
    checklist_fa: list[str]


class PulseAdviseResponse(BaseModel):
    recommended_profile_id: str
    profiles: list[PulseProfileOption]
    reality_front: PulseRealityFrontAdvice
    warnings: list[str] = Field(default_factory=list)


class HpxPulseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    iran_public_ip: str = Field(min_length=7, max_length=45)
    abroad_public_ip: str = Field(min_length=7, max_length=45)
    goal: PulseGoal = "balanced"
    cpu_cores: int = Field(default=1, ge=1, le=128)
    ram_mb: int = Field(default=1024, ge=256)
    udp_reachable: bool | None = None
    packet_loss_pct: float | None = Field(default=None, ge=0, le=100)
    profile_id: str | None = None
    control_port: int = Field(default=9067, ge=1024, le=65535)
    port_forwards: list[str] = Field(default_factory=list)
    domain: str | None = Field(default=None, max_length=255)
    sni_hint: str | None = Field(default=None, max_length=255)
    note: str | None = Field(default=None, max_length=512)


class HpxPulseResponse(BaseModel):
    id: int
    name: str
    status: PulseStatus
    enabled: bool
    engine: PulseEngine
    profile_id: str
    goal: PulseGoal
    tunnel_mode: str
    carrier: str | None
    preset: str
    iran_public_ip: str
    abroad_public_ip: str
    control_port: int
    local_ip_iran: str
    local_ip_abroad: str
    port_forwards: list[str]
    domain: str | None
    sni_hint: str | None
    note: str | None
    advice: PulseAdviseResponse | None = None
    iran_claimed: bool = False
    abroad_claimed: bool = False
    iran_agent_host: str | None = None
    abroad_agent_host: str | None = None
    iran_agent_last_seen: dt | None = None
    abroad_agent_last_seen: dt | None = None
    iran_join_expires_at: dt | None = None
    abroad_join_expires_at: dt | None = None
    message: str | None = None
    latency_ms: float | None = None
    packet_loss_pct: float | None = None
    created_at: dt

    model_config = ConfigDict(from_attributes=True)


class HpxPulseActionResponse(BaseModel):
    pulse: HpxPulseResponse
    message: str | None = None
    iran_join_token: str | None = None
    iran_join_command: str | None = None
    iran_join_command_alt: str | None = None
    abroad_join_token: str | None = None
    abroad_join_command: str | None = None
    abroad_join_command_alt: str | None = None
    iran_join_expires_at: dt | None = None
    abroad_join_expires_at: dt | None = None


class HpxPulsesResponse(BaseModel):
    pulses: list[HpxPulseResponse]
    total: int


class HpxPulseAgentClaimRequest(BaseModel):
    join_token: str = Field(min_length=8, max_length=256)
    host: str = Field(min_length=1, max_length=255)
    side: PulseSide


class HpxPulseAgentBootstrap(BaseModel):
    pulse_id: int
    name: str
    side: PulseSide
    agent_key: str
    tunnel_toml: str
    config_hash: str
    control_port: int
    abroad_public_ip: str
    iran_public_ip: str
    tunnel_mode: str = "direct_l3"
    port_forwards: list[str] = Field(default_factory=list)
    agent_assets_base: str | None = None


class HpxPulseAgentConfigResponse(BaseModel):
    pulse_id: int
    name: str
    side: PulseSide
    tunnel_toml: str
    config_hash: str
    desired_status: PulseStatus
    agent_command: str | None = None
    enabled: bool = True
    tunnel_mode: str = "direct_l3"
    control_port: int = 9067
    iran_public_ip: str | None = None
    abroad_public_ip: str | None = None
    port_forwards: list[str] = Field(default_factory=list)


class HpxPulseAgentHeartbeatRequest(BaseModel):
    status: PulseStatus = "running"
    host: str | None = None
    message: str | None = None
    latency_ms: float | None = None
    packet_loss_pct: float | None = None
    tunnel_running: bool = Field(default=False, validation_alias=AliasChoices("tunnel_running", "backpack_running"))
    iface_up: bool = False
    forward_ok: bool | None = None


class HpxPulseAgentAckRequest(BaseModel):
    command: str
    status: str
    message: str | None = None
