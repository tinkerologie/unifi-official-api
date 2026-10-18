"""LiveView models for UniFi Protect API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LiveViewSlot(BaseModel):
    """Camera slot configuration within a LiveView."""

    cameras: list[str] = Field(default_factory=list, description="Camera IDs in this slot")
    cycle_mode: str = Field(
        "none", alias="cycleMode", description="Cycle mode (none, time, motion)"
    )
    cycle_interval: int = Field(10, alias="cycleInterval", description="Cycle interval in seconds")

    model_config = {"populate_by_name": True, "extra": "allow"}


class LiveView(BaseModel):
    """UniFi Protect LiveView configuration model."""

    id: str = Field(..., description="LiveView primary key")
    model_key: str = Field("liveview", alias="modelKey")
    name: str = Field(..., description="LiveView name")
    is_default: bool = Field(
        False, alias="isDefault", description="Whether this is the default liveview"
    )
    is_global: bool = Field(
        False, alias="isGlobal", description="Whether liveview is shared across users"
    )
    owner: str | None = Field(default=None, description="User ID of the liveview owner")
    layout: int = Field(1, description="Grid layout size (1-26)")
    slots: list[LiveViewSlot] = Field(default_factory=list, description="Camera slot assignments")

    model_config = {"populate_by_name": True, "extra": "allow"}

    @property
    def camera_ids(self) -> list[str]:
        """Get all camera IDs across all slots."""
        cameras: list[str] = []
        for slot in self.slots:
            cameras.extend(slot.cameras)
        return cameras
