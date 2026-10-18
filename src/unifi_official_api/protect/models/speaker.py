"""Speaker models for UniFi Protect API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SpeakerState(BaseModel):
    """Speaker state information."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    status: str = "idle"
    mode: str = "default"


class SpeakerFeatureFlags(BaseModel):
    """Speaker hardware feature flags."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    has_mic: bool = Field(default=False, alias="hasMic")


class Speaker(BaseModel):
    """UniFi Protect speaker device."""

    id: str
    mac: str | None = None
    name: str | None = None
    type: str | None = None
    model: str | None = None
    model_key: str | None = Field(default="speaker", alias="modelKey")
    state: str | None = None
    firmware_version: str | None = Field(default=None, alias="firmwareVersion")
    hardware_revision: str | None = Field(default=None, alias="hardwareRevision")
    uptime: int | None = None
    last_seen: datetime | None = Field(default=None, alias="lastSeen")
    connected_since: datetime | None = Field(default=None, alias="connectedSince")
    is_connected: bool = Field(default=False, alias="isConnected")
    connection_type: str | None = Field(default=None, alias="connectionType")
    bridge: str | None = None
    volume: int | None = None
    mic_volume: int = Field(default=100, alias="micVolume")
    is_mic_enabled: bool = Field(default=False, alias="isMicEnabled")
    speaker_state: SpeakerState | dict[str, Any] | str | None = Field(
        default=None, alias="speakerState"
    )
    feature_flags: SpeakerFeatureFlags | dict[str, Any] | None = Field(
        default=None, alias="featureFlags"
    )

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    @property
    def display_name(self) -> str:
        """Return display name for the speaker."""
        return self.name or self.mac or self.id


__all__ = ["Speaker", "SpeakerFeatureFlags", "SpeakerState"]
