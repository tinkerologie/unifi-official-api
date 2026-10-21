"""Relay models for UniFi Protect API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RelayOutput(BaseModel):
    """Output channel on a UniFi Protect relay."""

    id: str | None = None
    name: str | None = None
    mode: str | None = None
    is_active: bool | None = Field(default=None, alias="isActive")
    duration_ms: int | None = Field(default=None, alias="durationMs")

    model_config = {"populate_by_name": True, "extra": "allow"}


class Relay(BaseModel):
    """UniFi Protect relay device."""

    id: str
    mac: str | None = None
    name: str | None = None
    type: str | None = None
    model: str | None = None
    model_key: str | None = Field(default="relay", alias="modelKey")
    state: str | None = None
    firmware_version: str | None = Field(default=None, alias="firmwareVersion")
    hardware_revision: str | None = Field(default=None, alias="hardwareRevision")
    uptime: int | None = None
    last_seen: datetime | None = Field(default=None, alias="lastSeen")
    connected_since: datetime | None = Field(default=None, alias="connectedSince")
    is_connected: bool = Field(default=False, alias="isConnected")
    connection_type: str | None = Field(default=None, alias="connectionType")
    bridge: str | None = None
    outputs: list[RelayOutput | dict[str, Any]] | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}

    @property
    def display_name(self) -> str:
        """Return display name for the relay."""
        return self.name or self.mac or self.id
