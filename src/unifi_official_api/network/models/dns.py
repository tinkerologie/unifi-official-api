"""DNS policy models for UniFi Network API."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DNSPolicyType(StrEnum):
    """DNS record/policy types."""

    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"
    MX = "MX"
    TXT = "TXT"
    SRV = "SRV"
    PTR = "PTR"
    FORWARD_DOMAIN = "FORWARD_DOMAIN"
    A_RECORD = "A_RECORD"
    AAAA_RECORD = "AAAA_RECORD"
    CNAME_RECORD = "CNAME_RECORD"
    MX_RECORD = "MX_RECORD"
    TXT_RECORD = "TXT_RECORD"
    SRV_RECORD = "SRV_RECORD"

    @classmethod
    def _missing_(cls, value: object) -> DNSPolicyType | None:
        """Handle unknown DNS record types."""
        if isinstance(value, str):
            upper = value.upper()
            for member in cls:
                if member.value == upper:
                    return member
        return None


DNSRecordType = DNSPolicyType


class DNSPolicyMetadata(BaseModel):
    """Metadata for a DNS policy."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    origin: str | None = None


class DNSPolicy(BaseModel):
    """Model representing a UniFi Network DNS policy."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str | None = None
    type: DNSPolicyType | str
    enabled: bool = True
    domain: str | None = None
    ipv4_address: str | None = Field(default=None, alias="ipv4Address")
    ipv6_address: str | None = Field(default=None, alias="ipv6Address")
    target_domain: str | None = Field(default=None, alias="targetDomain")
    mail_server_domain: str | None = Field(default=None, alias="mailServerDomain")
    Text: str | None = Field(default=None, alias="text")
    server_domain: str | None = Field(default=None, alias="serverDomain")
    ip_address: str | None = Field(default=None, alias="ipAddress")
    ttl_seconds: int | None = Field(default=None, alias="ttlSeconds")
    service: str | None = None
    protocol: str | None = None
    port: int | None = None
    weight: int | None = None
    priority: int | None = None
    metadata: DNSPolicyMetadata | dict[str, Any] | None = None

    @property
    def is_user_defined(self) -> bool:
        """Check if this DNS policy was user-defined."""
        if isinstance(self.metadata, DNSPolicyMetadata):
            return self.metadata.origin == "USER_DEFINED"
        if isinstance(self.metadata, dict):
            return self.metadata.get("origin") == "USER_DEFINED"
        return False

    @property
    def value(self) -> str | None:
        """Return the primary record value regardless of record type."""
        return (
            self.ipv4_address
            or self.ipv6_address
            or self.target_domain
            or self.mail_server_domain
            or self.Text
            or self.server_domain
            or self.ip_address
        )

    @property
    def display_name(self) -> str:
        """Return display name with type and value."""
        domain = self.domain or self.id or "unknown"
        val = self.value
        if val:
            return f"{domain} ({self.type}: {val})"
        return f"{domain} ({self.type})"


__all__ = [
    "DNSPolicy",
    "DNSPolicyMetadata",
    "DNSPolicyType",
    "DNSRecordType",
]
