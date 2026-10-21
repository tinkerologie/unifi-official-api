"""Connected client models for UniFi Mobility."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MobilityDeviceClient(BaseModel):
    """Client device connected to a mobility router."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    mac: str
    name: str
    type: str = "WIRELESS"
    connection_status: str = Field(alias="connection_status")
    ip_address: str = Field(alias="ip_address")
    is_blocked: bool = Field(default=False, alias="is_blocked")
    wifi_experience: int | None = Field(default=None, alias="wifi_experience")
