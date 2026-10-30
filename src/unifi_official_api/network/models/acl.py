"""ACL (Access Control List) rule models for UniFi Network API."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field


class ACLRuleType(StrEnum):
    """ACL rule type."""

    IPV4 = "IPV4"
    MAC = "MAC"


class ACLAction(StrEnum):
    """ACL rule actions."""

    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


class ACLProtocol(StrEnum):
    """Network protocols for ACL rules."""

    TCP = "TCP"
    UDP = "UDP"


class MetadataOrigin(StrEnum):
    """Metadata origin type."""

    USER_DEFINED = "USER_DEFINED"
    SYSTEM_DEFINED = "SYSTEM_DEFINED"
    DERIVED = "DERIVED"
    ORCHESTRATED = "ORCHESTRATED"


class ACLMetadata(BaseModel):
    """ACL rule metadata."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    origin: MetadataOrigin | str = Field(..., description="Rule origin", union_mode="left_to_right")


class ACLDeviceFilter(BaseModel):
    """Filter for enforcing devices."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    device_ids: list[str] | None = Field(
        None, alias="deviceIds", description="Switch device IDs for enforcement"
    )


class ACLSourceFilter(BaseModel):
    """Traffic source filtering configuration."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    network_ids: list[str] | None = Field(None, alias="networkIds")
    mac_addresses: list[str] | None = Field(None, alias="macAddresses")
    ip_addresses: list[str] | None = Field(None, alias="ipAddresses")
    port_ranges: list[str] | None = Field(None, alias="portRanges")


class ACLDestinationFilter(BaseModel):
    """Traffic destination filtering configuration."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    network_ids: list[str] | None = Field(None, alias="networkIds")
    mac_addresses: list[str] | None = Field(None, alias="macAddresses")
    ip_addresses: list[str] | None = Field(None, alias="ipAddresses")
    port_ranges: list[str] | None = Field(None, alias="portRanges")


class ACLTrafficSource(BaseModel):
    """Traffic source or destination filter for ACL rules."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    type: str | None = None
    ips: list[str] = Field(default_factory=list)
    macs: list[str] = Field(default_factory=list)
    network_ids: list[str] = Field(default_factory=list, alias="networkIds")
    ports: list[int] = Field(default_factory=list)
    specific_mac_addresses: list[str] = Field(default_factory=list, alias="specificMacAddresses")
    ip_addresses_or_subnets: list[str] = Field(default_factory=list, alias="ipAddressesOrSubnets")
    ports_filter: list[int | str] = Field(default_factory=list, alias="portsFilter")
    network_id: str | None = Field(default=None, alias="networkId")


class ACLRule(BaseModel):
    """Model representing a UniFi Network ACL rule."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str | None = None
    type: ACLRuleType | str = Field(default=ACLRuleType.IPV4, union_mode="left_to_right")
    name: str
    description: str | None = None
    enabled: bool = True
    action: ACLAction | str = Field(union_mode="left_to_right")
    index: int | None = None
    enforcing_device_ids: list[str] = Field(default_factory=list, alias="enforcingDeviceIds")
    enforcing_device_filter: ACLDeviceFilter | None = Field(
        default=None, alias="enforcingDeviceFilter"
    )
    source_filter: ACLSourceFilter | ACLTrafficSource | dict[str, Any] | None = Field(
        default=None, alias="sourceFilter"
    )
    destination_filter: ACLDestinationFilter | ACLTrafficSource | dict[str, Any] | None = Field(
        default=None, alias="destinationFilter"
    )
    protocol_filter: list[Annotated[ACLProtocol | str, Field(union_mode="left_to_right")]] = Field(
        default_factory=list, alias="protocolFilter"
    )
    network_id_filter: str | None = Field(default=None, alias="networkIdFilter")
    # The model branch stays first; it is inexact once a nested field has a
    # union mode, so left-to-right keeps parsing dicts into ACLMetadata (#70).
    metadata: ACLMetadata | dict[str, Any] | None = Field(default=None, union_mode="left_to_right")

    @property
    def display_name(self) -> str:
        """Return display name with action."""
        return f"{self.name} ({self.action})"

    @property
    def is_user_defined(self) -> bool:
        """Check if rule is user-defined (can be modified/deleted)."""
        if self.metadata is None:
            return True
        if isinstance(self.metadata, ACLMetadata):
            return self.metadata.origin == MetadataOrigin.USER_DEFINED
        if isinstance(self.metadata, dict):
            return self.metadata.get("origin") == "USER_DEFINED"
        return False


class OrderedACLRuleIds(BaseModel):
    """Ordered user-defined ACL rule IDs."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    user_defined_acl_rule_ids: list[str] = Field(
        default_factory=list, alias="userDefinedAclRuleIds"
    )


class ACLRuleOrdering(BaseModel):
    """Model representing the ordering of user-defined ACL rules."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    ordered_acl_rule_ids: list[str] = Field(default_factory=list, alias="orderedAclRuleIds")


class ACLPolicyOrdering(BaseModel):
    """ACL policy ordering response/update model."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    ordered_acl_rule_ids: OrderedACLRuleIds | list[str] = Field(
        default_factory=OrderedACLRuleIds, alias="orderedAclRuleIds"
    )


__all__ = [
    "ACLAction",
    "ACLDestinationFilter",
    "ACLDeviceFilter",
    "ACLMetadata",
    "ACLPolicyOrdering",
    "ACLProtocol",
    "ACLRule",
    "ACLRuleOrdering",
    "ACLRuleType",
    "ACLSourceFilter",
    "ACLTrafficSource",
    "MetadataOrigin",
    "OrderedACLRuleIds",
]
