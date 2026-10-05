from pydantic import BaseModel, ConfigDict, Field


class RealityScanRequest(BaseModel):
    target: str = Field(min_length=1, max_length=253, description="host or host:port to probe (port defaults to 443)")
    timeout: float | None = Field(
        default=None, ge=1, le=20, description="Per-probe timeout in seconds (1-20, default 10)"
    )
    check_iran_path: bool = Field(
        default=True,
        description="Also score Iran/Pulse fitness (affinity + reachability of Pulse Iran IPs)",
    )


class RealityPulsePathCheck(BaseModel):
    pulse_id: int
    name: str
    iran_ip: str
    port: int
    reachable: bool
    latency_ms: int | None = None
    detail: str | None = None


class RealityIranPath(BaseModel):
    score: int = Field(ge=0, le=100)
    grade: str  # excellent | good | fair | poor | n/a
    iran_affinity: bool = False
    affinity_reason: str | None = None
    pulse_checks: list[RealityPulsePathCheck] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class RealityScanResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    target: str
    host: str
    ip: str | None = None
    port: int
    sni: str | None = None
    sni_discovered: bool = False

    feasible: bool
    tls13: bool
    tls_version: str | None = None
    h2: bool
    alpn: str | None = None

    x25519: bool | None = None
    post_quantum: bool | None = None
    curve: str | None = None

    h3: bool = False

    cert_valid: bool
    cert_subject: str | None = None
    cert_issuer: str | None = None
    not_after: str | None = None
    server_names: list[str] = Field(default_factory=list)

    latency_ms: int | None = None
    reason: str | None = None

    iran_path: RealityIranPath | None = None
