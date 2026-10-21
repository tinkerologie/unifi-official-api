"""Device models for UniFi Site Manager."""

from pydantic import BaseModel, ConfigDict, Field


class SiteManagerDevice(BaseModel):
    """Hardware device managed under a host."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str | None = None
    mac: str = ""
    model: str | None = None
    name: str | None = None
    ip: str | None = None
    state: str = "CONNECTED"


class SiteManagerHostDevices(BaseModel):
    """Host device group in Site Manager."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    host_id: str = Field(alias="hostId")
    host_name: str | None = Field(default=None, alias="hostName")
    devices: list[SiteManagerDevice] = Field(default_factory=list)
    updated_at: str | None = Field(default=None, alias="updatedAt")


class DeviceListResponse(BaseModel):
    """Response envelope for listing devices."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    data: list[SiteManagerHostDevices] = Field(default_factory=list)
    next_token: str | None = Field(default=None, alias="nextToken")
