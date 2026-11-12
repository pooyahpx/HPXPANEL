from datetime import datetime as dt
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.utils.helpers import fix_datetime_timezone

PulseGoal = Literal["stealth", "balanced", "speed", "mobile", "hard", "fast", "spoof"]
PulseSpoofProfile = Literal["udp", "icmp", "tcp", "icmpv6", "proto58", "ipip", "gre"]


class PulseSpoofConfig(BaseModel):
    """Direct Spoof carrier settings stored on the pulse (both agents share the pair)."""

    profile: PulseSpoofProfile = "udp"
    stealth: bool = False
    src_ip: str = ""
    src_pool: list[str] = Field(default_factory=list)
    iran_src_ip: str = ""
    abroad_src_ip: str = ""
    mtu: int = Field(default=0, ge=0, le=9000)
    sockbuf: int = Field(default=0, ge=0, le=268435456)
    icmp_reply: bool = False
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
    mss: int | None = None
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
    spoof_config: PulseSpoofConfig | None = None
    auto_restart_interval_minutes: int | None = Field(default=None, ge=0, le=10080)
    auto_heal_enabled: bool = True
    backup_pulse_id: int | None = Field(default=None, ge=1)
    auto_failover: bool = False
    auto_failback: bool = True
    priority: int = Field(default=0, ge=0, le=100)


class HpxPulseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=40)
    iran_public_ip: str | None = Field(default=None, min_length=7, max_length=45)
    abroad_public_ip: str | None = Field(default=None, min_length=7, max_length=45)
    goal: PulseGoal | None = None
    profile_id: str | None = None
    control_port: int | None = Field(default=None, ge=1024, le=65535)
    port_forwards: list[str] | None = None
    domain: str | None = Field(default=None, max_length=255)
    sni_hint: str | None = Field(default=None, max_length=255)
    note: str | None = Field(default=None, max_length=512)
    spoof_config: PulseSpoofConfig | None = None
    enabled: bool | None = None
    auto_restart_interval_minutes: int | None = Field(default=None, ge=0, le=10080)
    auto_heal_enabled: bool | None = None
    backup_pulse_id: int | None = Field(default=None, ge=1)
    auto_failover: bool | None = None
    auto_failback: bool | None = None
    priority: int | None = Field(default=None, ge=0, le=100)


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
    spoof_config: PulseSpoofConfig | None = None
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
    auto_restart_interval_minutes: int | None = None
    last_auto_restart_at: dt | None = None
    auto_heal_enabled: bool = True
    last_heal_at: dt | None = None
    last_heal_action: str | None = None
    last_health_check: dt | None = None
    backup_pulse_id: int | None = None
    auto_failover: bool = False
    auto_failback: bool = True
    failover_active: bool = False
    priority: int = 0
    last_failover_at: dt | None = None
    created_at: dt
    path_ping: dict | None = None
    bytes_up: int = 0
    bytes_down: int = 0

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
    diag: dict | None = None
    # Absolute counters from the agent (bp0 or TCP socket estimate). Panel diffs them.
    iface_rx_bytes: int | None = Field(default=None, ge=0)
    iface_tx_bytes: int | None = Field(default=None, ge=0)


class HpxPulseAgentAckRequest(BaseModel):
    command: str
    status: str
    message: str | None = None


class HpxPulseDiagCheck(BaseModel):
    group: str
    name: str
    level: Literal["ok", "warn", "fail", "info"]
    detail: str
    fix: str = ""


class HpxPulseDiagnoseResponse(BaseModel):
    pulse_id: int
    name: str
    ok: int
    warn: int
    fail: int
    healthy: bool
    headline: str
    primary_fix: str = ""
    checks: list[HpxPulseDiagCheck]
    engine_pin: str | None = None
    diag_report: dict | None = None
    probe_queued: bool = False
    hint: str | None = None


class HpxPulsePathPingRequest(BaseModel):
    """Queue TCP/UDP path samples from abroad agent → Iran (XRayMesh-style live ping).

    Default target is ``forward`` (user path). Probing ``control`` with raw TCP on
    reverse/stealth tunnels can accept-then-reset the control session and drop the
    live tunnel — agents coerce control→forward for reverse_* modes.
    """

    proto: Literal["tcp", "udp"] = "tcp"
    count: int = Field(default=4, ge=1, le=20)
    target: Literal["control", "forward"] = "forward"


class HpxPulsePathPingReply(BaseModel):
    seq: int
    status: Literal["ok", "timeout", "error"]
    time_ms: float | None = None
    detail: str = ""


class HpxPulsePathPingResponse(BaseModel):
    pulse_id: int
    name: str
    queued: bool
    proto: Literal["tcp", "udp"]
    count: int
    target: Literal["control", "forward"]
    port: int | None = None
    hint: str | None = None
    path_ping: dict | None = None


class PulseUsageShareQuery(BaseModel):
    """Time range for ranking pulses by traffic share. Defaults to the last 7 days."""

    start: dt | None = Field(default=None, examples=["2024-01-01T00:00:00+03:30"])
    end: dt | None = Field(default=None, examples=["2024-01-31T23:59:59+03:30"])

    @field_validator("start", "end", mode="before")
    @classmethod
    def validate_datetimes(cls, value):
        if not value:
            return value
        return fix_datetime_timezone(value)


class PulseUsageShareItem(BaseModel):
    pulse_id: int
    name: str
    bytes: int = 0
    percent: float = 0.0


class PulseUsageShareResponse(BaseModel):
    total_bytes: int = 0
    items: list[PulseUsageShareItem] = Field(default_factory=list)
    start: dt | None = None
    end: dt | None = None
