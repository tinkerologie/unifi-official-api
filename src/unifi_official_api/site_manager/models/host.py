"""Host models for UniFi Site Manager."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class HostUserData(BaseModel):
    """User-defined data for a host."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    name: str | None = None


class HostReportedState(BaseModel):
    """Reported runtime state for a host."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    state: str = "CONNECTED"
    hostname: str | None = None
    ip_address: str | None = Field(default=None, alias="ipAddress")
    version: str | None = None


class Host(BaseModel):
    """UniFi console host."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str
    hardware_id: str | None = Field(default=None, alias="hardwareId")
    type: str | None = None
    ip_address: str | None = Field(default=None, alias="ipAddress")
    owner: bool | None = None
    is_blocked: bool = Field(default=False, alias="isBlocked")
    registration_time: str | None = Field(default=None, alias="registrationTime")
    last_connection_state_change: str | None = Field(
        default=None, alias="lastConnectionStateChange"
    )
    latest_backup_time: str | None = Field(default=None, alias="latestBackupTime")
    user_data: HostUserData | None = Field(default=None, alias="userData")
    reported_state: HostReportedState | None = Field(default=None, alias="reportedState")


class HostListResponse(BaseModel):
    """Response envelope for listing hosts."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    data: list[Host] = Field(default_factory=list)
    next_token: str | None = Field(default=None, alias="nextToken")
