"""Configuration request models for UniFi Mobility."""

from pydantic import BaseModel, ConfigDict, Field


class UpdateDeviceNameReq(BaseModel):
    """Update device name payload."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    name: str


class UpdateNetworkReq(BaseModel):
    """Update LAN / DHCP settings."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    host_address: str | None = Field(default=None, alias="host_address")
    dhcp_mode: str | None = Field(default=None, alias="dhcp_mode")
    dhcp_range_start: str | None = Field(default=None, alias="dhcp_range_start")
    dhcp_range_stop: str | None = Field(default=None, alias="dhcp_range_stop")
    dhcp_lease_time: int | None = Field(default=None, alias="dhcp_lease_time")


class UpdateWirelessReq(BaseModel):
    """Update WiFi settings."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    ssid: str
    password: str
