"""Switching models for UniFi Network."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .stack import SwitchStack, SwitchStackMember, SwitchStackPage


class LagType(StrEnum):
    """Link aggregation group types."""

    LOCAL = "LOCAL"
    MULTI_CHASSIS = "MULTI_CHASSIS"
    SWITCH_STACK = "SWITCH_STACK"


class LagMember(BaseModel):
    """Member of a LAG."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    device_id: str | None = Field(default=None, alias="deviceId")
    switch_mac: str | None = Field(default=None, alias="switchMac")
    port_idxs: list[int] = Field(default_factory=list, alias="portIdxs")


class Lag(BaseModel):
    """Link Aggregation Group (LAG)."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    name: str | None = None
    type: str = "LOCAL"
    mode: str | None = None
    members: list[LagMember] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None


class LagPage(BaseModel):
    """Paginated list of LAGs."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    data: list[Lag] = Field(default_factory=list)
    count: int = 0
    limit: int = 0
    offset: int = 0
    total_count: int = Field(default=0, alias="totalCount")


class McLagPeer(BaseModel):
    """MC-LAG peer configuration."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    device_id: str | None = Field(default=None, alias="deviceId")
    switch_mac: str | None = Field(default=None, alias="switchMac")
    role: str | None = None
    interconnect_port_idxs: list[int] = Field(default_factory=list, alias="interconnectPortIdxs")


class McLagDomain(BaseModel):
    """Multi-Chassis LAG domain."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    name: str | None = None
    domain_id: int | None = Field(default=None, alias="domainId")
    peers: list[McLagPeer] = Field(default_factory=list)
    lags: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None


class McLagDomainPage(BaseModel):
    """Paginated list of MC-LAG domains."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    data: list[McLagDomain] = Field(default_factory=list)
    count: int = 0
    limit: int = 0
    offset: int = 0
    total_count: int = Field(default=0, alias="totalCount")


__all__ = [
    "Lag",
    "LagMember",
    "LagPage",
    "LagType",
    "McLagDomain",
    "McLagDomainPage",
    "McLagPeer",
    "SwitchStack",
    "SwitchStackMember",
    "SwitchStackPage",
]
