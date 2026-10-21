"""Chime models for UniFi Protect API."""

from datetime import datetime

from pydantic import BaseModel, Field


class ChimeRingSetting(BaseModel):
    """Per-camera ring configuration on a chime."""

    camera_id: str | None = Field(default=None, alias="cameraId")
    repeat_times: int | None = Field(default=None, alias="repeatTimes")
    ringtone_id: str | None = Field(default=None, alias="ringtoneId")
    volume: int | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class Chime(BaseModel):
    """Model representing a UniFi Protect chime."""

    id: str
    mac: str
    name: str | None = None
    type: str | None = None
    model: str | None = None
    state: str | None = None
    firmware_version: str | None = Field(default=None, alias="firmwareVersion")
    hardware_revision: str | None = Field(default=None, alias="hardwareRevision")
    uptime: int | None = None
    last_seen: datetime | None = Field(default=None, alias="lastSeen")
    connected_since: datetime | None = Field(default=None, alias="connectedSince")
    is_connected: bool = Field(default=False, alias="isConnected")
    volume: int = Field(default=100)
    ring_tone: str | None = Field(default=None, alias="ringTone")
    repeat_times: int = Field(default=1, alias="repeatTimes")
    camera: str | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}

    @property
    def display_name(self) -> str:
        """Get the display name for the chime."""
        return self.name or self.mac
