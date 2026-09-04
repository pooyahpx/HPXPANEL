from datetime import datetime as dt

from pydantic import BaseModel, ConfigDict, Field


class FleetNodeSummary(BaseModel):
    id: int
    name: str
    status: str
    address: str | None = None
    node_version: str | None = None
    xray_version: str | None = None
    last_status_change: dt | None = None

    model_config = ConfigDict(from_attributes=True)


class FleetTunnelSummary(BaseModel):
    id: int
    name: str
    status: str
    agent_claimed: bool = False
    agent_last_seen: dt | None = None
    agent_host: str | None = None

    model_config = ConfigDict(from_attributes=True)


class FleetPulseSummary(BaseModel):
    id: int
    name: str
    status: str
    iran_claimed: bool = False
    abroad_claimed: bool = False
    iran_agent_last_seen: dt | None = None
    abroad_agent_last_seen: dt | None = None
    iran_agent_host: str | None = None
    abroad_agent_host: str | None = None

    model_config = ConfigDict(from_attributes=True)


class FleetSummaryResponse(BaseModel):
    generated_at: dt
    nodes: list[FleetNodeSummary] = Field(default_factory=list)
    tunnels: list[FleetTunnelSummary] = Field(default_factory=list)
    pulses: list[FleetPulseSummary] = Field(default_factory=list)
    totals: dict[str, int] = Field(default_factory=dict)
