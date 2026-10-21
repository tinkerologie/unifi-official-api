"""Device models for UniFi Mobility."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DeviceLocation(BaseModel):
    """GPS location coordinates for a mobility device."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    latitude: float
    longitude: float
    last_updated: int = Field(alias="last_updated")


class MobilityDeviceSummary(BaseModel):
    """Lightweight mobility device representation in device lists."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    name: str
    model: str = "UMR"
    state: str = "CONNECTED"
    firmware_version: str = Field(alias="firmware_version")
    mac_address: str = Field(alias="mac_address")


class MobilityDeviceDetail(BaseModel):
    """Full detail of a UniFi Mobility device."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    name: str
    model: str = "UMR"
    state: str = "CONNECTED"
    firmware_version: str = Field(alias="firmware_version")
    mac_address: str = Field(alias="mac_address")
    wan_source: str | None = Field(default=None, alias="wan_source")
    wan_ip: str | None = Field(default=None, alias="wan_ip")
    enabled_wans: list[str] = Field(default_factory=list, alias="enabled_wans")
    isp: str | None = None
    lte_signal_level: str | None = Field(default=None, alias="lte_signal_level")
    cellular_data_usage_bytes: int | None = Field(default=None, alias="cellular_data_usage_bytes")
    cellular_data_limit_bytes: int | None = Field(default=None, alias="cellular_data_limit_bytes")
    memory_usage_percent: int | None = Field(default=None, alias="memory_usage_percent")
    uptime_seconds: int | None = Field(default=None, alias="uptime_seconds")
    client_count: int | None = Field(default=None, alias="client_count")
    host_address: str | None = Field(default=None, alias="host_address")
    poe_passthrough: bool | None = Field(default=None, alias="poe_passthrough")
    device_mode: str | None = Field(default=None, alias="device_mode")
    wifi_enabled: bool | None = Field(default=None, alias="wifi_enabled")
    wifi_ssid: str | None = Field(default=None, alias="wifi_ssid")
    tx_power_level: str | None = Field(default=None, alias="tx_power_level")
    vpn_profile_name: str | None = Field(default=None, alias="vpn_profile_name")
    vpn_status: str | None = Field(default=None, alias="vpn_status")
    location: DeviceLocation | None = None
