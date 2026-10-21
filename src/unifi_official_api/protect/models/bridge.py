"""Bridge models for UniFi Protect API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .link_station import LinkStation


class Bridge(BaseModel):
    """UniFi Protect bridge device."""

    id: str
    mac: str | None = None
    name: str | None = None
    type: str | None = None
    model: str | None = None
    model_key: str | None = Field(default="bridge", alias="modelKey")
    state: str | None = None
    firmware_version: str | None = Field(default=None, alias="firmwareVersion")
    hardware_revision: str | None = Field(default=None, alias="hardwareRevision")
    uptime: int | None = None
    last_seen: datetime | None = Field(default=None, alias="lastSeen")
    connected_since: datetime | None = Field(default=None, alias="connectedSince")
    is_connected: bool = Field(default=False, alias="isConnected")
    connection_host: str | None = Field(default=None, alias="connectionHost")
    clients: list[str | dict[str, Any]] = Field(default_factory=list)
    connected_cameras: list[str] | None = Field(default=None, alias="connectedCameras")
    max_clients: int | None = Field(default=None, alias="maxClients")

    model_config = {"populate_by_name": True, "extra": "allow"}

    @property
    def display_name(self) -> str:
        """Return display name for the bridge."""
        return self.name or self.mac or self.id


__all__ = ["Bridge", "LinkStation"]
