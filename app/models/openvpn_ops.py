from pydantic import BaseModel, ConfigDict, Field


class OpenVPNUserMonitorEntry(BaseModel):
    user_id: int
    username: str
    has_certificate: bool
    serial: str = ""
    fingerprint: str = ""
    online: bool = False
    connection_count: int = 0
    ips: dict[str, int] = Field(default_factory=dict)
    ip_protocol: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class OpenVPNNodeMonitoringResponse(BaseModel):
    node_id: int
    core_id: int | None = None
    core_name: str = ""
    pki_ready: bool = False
    listener_port: int | None = None
    listener_proto: str = ""
    users: list[OpenVPNUserMonitorEntry] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class OpenVPNHealthCheck(BaseModel):
    core_id: int
    node_id: int | None = None
    user_id: int | None = None
    pki_ready: bool = False
    ca_key_missing: bool = False
    node_connected: bool = False
    user_has_certificate: bool = False
    user_in_openvpn_group: bool = False
    host_configured: bool = False
    ready: bool = False
    issues: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class OpenVPNOnboardingRequest(BaseModel):
    core_id: int
    node_id: int
    group_name: str = Field(default="OpenVPN Users", max_length=128)
    host_address: str = Field(min_length=3, max_length=512)
    host_port: int | None = Field(default=None, ge=1, le=65535)
    test_username: str = Field(default="openvpn_test", min_length=3, max_length=32)

    model_config = ConfigDict(from_attributes=True)


class OpenVPNOnboardingResponse(BaseModel):
    core_id: int
    node_id: int
    group_id: int
    host_id: int
    user_id: int
    username: str
    subscription_url: str = ""
    health: OpenVPNHealthCheck

    model_config = ConfigDict(from_attributes=True)
