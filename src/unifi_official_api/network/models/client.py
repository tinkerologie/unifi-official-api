"""Client models for UniFi Network Integration v1 API."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ClientType(StrEnum):
    """Client connection types in the v1 API."""

    WIRED = "WIRED"
    WIRELESS = "WIRELESS"
    VPN = "VPN"
    TELEPORT = "TELEPORT"

    @classmethod
    def _missing_(cls, value: object) -> ClientType | None:
        """Handle lowercase or mixed-case client types."""
        if isinstance(value, str):
            upper = value.upper()
            for member in cls:
                if member.value == upper:
                    return member
        return None


class ClientAccess(BaseModel):
    """Client access information (guest/default access state)."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    type: str | None = None
    authorized: bool | None = None
    authorization_type: str | None = Field(default=None, alias="authorizationType")
    authorized_at: int | None = Field(default=None, alias="authorizedAt")
    expires_at: int | None = Field(default=None, alias="expiresAt")
    data_usage_limit_mbytes: int | None = Field(default=None, alias="dataUsageLimitMBytes")
    rx_rate_limit_kbps: int | None = Field(default=None, alias="rxRateLimitKbps")
    tx_rate_limit_kbps: int | None = Field(default=None, alias="txRateLimitKbps")
    data_usage_b: int | None = Field(default=None, alias="dataUsageB")


class Client(BaseModel):
    """Model representing a connected network client (station) in the v1 API."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    name: str | None = None
    type: ClientType | str | None = None
    ip: str | None = Field(default=None, alias="ipAddress")
    mac: str | None = Field(default=None, alias="macAddress")
    connected_at: datetime | str | None = Field(default=None, alias="connectedAt")
    uplink_device_id: str | None = Field(default=None, alias="uplinkDeviceId")
    access: ClientAccess | dict[str, Any] | None = None
    site_id: str | None = Field(default=None, alias="siteId")
    network_id: str | None = Field(default=None, alias="networkId")

    @field_validator("type", mode="before")
    @classmethod
    def _normalize_client_type(cls, value: Any) -> Any:
        """Normalize client type to known enum where possible."""
        if isinstance(value, str):
            for member in ClientType:
                if member.value == value or member.name == value.upper():
                    return member
        return value

    @model_validator(mode="before")
    @classmethod
    def _populate_id_fallback(cls, data: Any) -> Any:
        """Populate id from _id or mac if missing."""
        if not isinstance(data, dict):
            return data
        if "id" not in data or not data["id"]:
            fallback = data.get("_id") or data.get("macAddress") or data.get("mac")
            if fallback:
                data = {**data, "id": fallback}
        return data

    @property
    def display_name(self) -> str:
        """Return display name (name, hostname if present, MAC, or 'Unknown')."""
        hostname = getattr(self, "hostname", None)
        return self.name or hostname or self.mac or "Unknown"

    @property
    def ip_address(self) -> str | None:
        """Return IP address."""
        return self.ip

    @property
    def mac_address(self) -> str | None:
        """Return MAC address."""
        return self.mac


__all__ = [
    "Client",
    "ClientAccess",
    "ClientType",
]
