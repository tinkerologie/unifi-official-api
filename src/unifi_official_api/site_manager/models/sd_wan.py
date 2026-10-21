"""SD-WAN models for UniFi Site Manager."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SDWanConfig(BaseModel):
    """SD-WAN configuration summary."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    name: str
    type: str = "site-to-site"


class SDWanConfigDetail(BaseModel):
    """Detailed SD-WAN configuration."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    name: str
    type: str = "site-to-site"
    topologies: list[dict[str, Any]] = Field(default_factory=list)
    nodes: list[dict[str, Any]] = Field(default_factory=list)


class SDWanStatus(BaseModel):
    """SD-WAN network status."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    status: str = "HEALTHY"
    tunnels: list[dict[str, Any]] = Field(default_factory=list)
