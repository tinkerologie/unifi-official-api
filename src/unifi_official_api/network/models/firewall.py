"""Firewall models for UniFi Network Integration v1 API."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FirewallAction(StrEnum):
    """Firewall rule actions."""

    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REJECT = "REJECT"
    ACCEPT = "accept"
    DROP = "drop"
    DENY = "DENY"

    @classmethod
    def _missing_(cls, value: object) -> FirewallAction | None:
        """Handle unknown actions."""
        if isinstance(value, str):
            upper = value.upper()
            for member in cls:
                if member.value == upper:
                    return member
        return None


class FirewallActionConfig(BaseModel):
    """Action configuration for a v1 firewall policy."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    type: FirewallAction | str = FirewallAction.BLOCK
    allow_return_traffic: bool | None = Field(default=None, alias="allowReturnTraffic")


class FirewallProtocol(StrEnum):
    """Firewall protocols."""

    ALL = "all"
    TCP = "tcp"
    UDP = "udp"
    ICMP = "icmp"
    TCP_UDP = "tcp_udp"


class FirewallRule(BaseModel):
    """Model representing a UniFi Network v1 firewall policy."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    name: str
    description: str | None = None
    enabled: bool = True
    index: int | None = None
    site_id: str | None = Field(default=None, alias="siteId")
    logging_enabled: bool = Field(default=False, alias="loggingEnabled")
    # None when the console does not report it (Network before 11.0.97).
    report_flow_enabled: bool | None = Field(default=None, alias="reportFlowEnabled")
    logging: bool = False
    action: FirewallAction | FirewallActionConfig | dict[str, Any] | str = FirewallAction.BLOCK
    protocol: str | None = Field(default=None)
    source_zone_id: str | None = Field(default=None, alias="sourceZoneId")
    destination_zone_id: str | None = Field(default=None, alias="destinationZoneId")
    source_address: str | None = Field(default=None, alias="sourceAddress")
    destination_address: str | None = Field(default=None, alias="destinationAddress")
    source_port: str | None = Field(default=None, alias="sourcePort")
    destination_port: str | None = Field(default=None, alias="destinationPort")
    source: dict[str, Any] | None = None
    destination: dict[str, Any] | None = None
    ip_protocol_scope: dict[str, Any] | str | None = Field(default=None, alias="ipProtocolScope")
    connection_state_filter: list[str] | None = Field(default=None, alias="connectionStateFilter")
    ipsec_filter: str | None = Field(default=None, alias="ipsecFilter")
    schedule: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def _populate_id_fallback(cls, data: Any) -> Any:
        """Populate id from _id if missing."""
        if not isinstance(data, dict):
            return data
        if "id" not in data and "_id" in data:
            data = {**data, "id": data["_id"]}
        return data

    @property
    def action_type(self) -> str:
        """Return the action type string regardless of whether action is a dict or enum."""
        if isinstance(self.action, FirewallActionConfig):
            return str(self.action.type)
        if isinstance(self.action, dict):
            return str(self.action.get("type", "BLOCK"))
        return str(self.action)

    @property
    def display_name(self) -> str:
        """Return display name."""
        return self.name

    @property
    def loggingEnabled(self) -> bool:
        """CamelCase alias for logging_enabled."""
        return self.logging_enabled


class FirewallZone(BaseModel):
    """Model representing a UniFi Network v1 firewall zone."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str | None = None
    name: str
    site_id: str | None = Field(default=None, alias="siteId")
    network_ids: list[str] = Field(default_factory=list, alias="networkIds")
    metadata: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def _populate_id_fallback(cls, data: Any) -> Any:
        """Populate id from _id if missing."""
        if not isinstance(data, dict):
            return data
        if "id" not in data and "_id" in data:
            data = {**data, "id": data["_id"]}
        return data

    @property
    def display_name(self) -> str:
        """Return display name."""
        return self.name


class OrderedFirewallPolicyIds(BaseModel):
    """Ordered firewall policy IDs broken down by system vs user-defined."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    before_system_defined: list[str] = Field(default_factory=list, alias="beforeSystemDefined")
    after_system_defined: list[str] = Field(default_factory=list, alias="afterSystemDefined")


class FirewallPolicyOrdering(BaseModel):
    """Firewall policy ordering response/update model."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    ordered_firewall_policy_ids: OrderedFirewallPolicyIds = Field(
        default_factory=OrderedFirewallPolicyIds,
        alias="orderedFirewallPolicyIds",
    )


__all__ = [
    "FirewallAction",
    "FirewallActionConfig",
    "FirewallPolicyOrdering",
    "FirewallProtocol",
    "FirewallRule",
    "FirewallZone",
    "OrderedFirewallPolicyIds",
]
