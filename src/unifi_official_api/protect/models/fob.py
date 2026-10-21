"""Keypad and fob models for UniFi Protect API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FobKeypadSettings(BaseModel):
    """
    Keypad settings of a fob with a PIN keypad (Protect 7.3.70+).

    Read-only in the public API: ``PATCH /v1/fobs/{id}`` accepts ``name`` only.
    Fields are optional and unconstrained so an out-of-range value cannot make
    the endpoint drop the fob.
    """

    beep_enabled: bool | None = Field(default=None, alias="beepEnabled")
    beep_volume: int | None = Field(default=None, alias="beepVolume")  # 0-100

    model_config = {"populate_by_name": True, "extra": "allow"}


class FobArmControlSettings(BaseModel):
    """Which external arm profiles a fob arms and disarms (Protect 7.3.70+)."""

    enabled: bool | None = None
    arm_profile_id: str | None = Field(default=None, alias="armProfileId")
    night_profile_id: str | None = Field(default=None, alias="nightProfileId")

    model_config = {"populate_by_name": True, "extra": "allow"}


class KeypadFob(BaseModel):
    """UniFi Protect keypad or fob device."""

    id: str
    mac: str | None = None
    name: str | None = None
    type: str | None = None
    model: str | None = None
    model_key: str | None = Field(default="fob", alias="modelKey")
    state: str | None = None
    away_state: str | None = Field(default=None, alias="awayState")
    firmware_version: str | None = Field(default=None, alias="firmwareVersion")
    hardware_revision: str | None = Field(default=None, alias="hardwareRevision")
    uptime: int | None = None
    last_seen: datetime | None = Field(default=None, alias="lastSeen")
    connected_since: datetime | None = Field(default=None, alias="connectedSince")
    is_connected: bool = Field(default=False, alias="isConnected")
    connection_type: str | None = Field(default=None, alias="connectionType")
    bridge: str | None = None
    battery_status: dict[str, Any] | None = Field(default=None, alias="batteryStatus")
    user_id: str | None = Field(default=None, alias="userId")
    button_labels: str | dict[str, Any] | list[Any] | None = Field(
        default=None, alias="buttonLabels"
    )
    last_event: int | float | str | dict[str, Any] | None = Field(default=None, alias="lastEvent")
    feature_flags: dict[str, Any] | None = Field(default=None, alias="featureFlags")
    wireless_connection_state: dict[str, Any] | None = Field(
        default=None, alias="wirelessConnectionState"
    )
    keypad_settings: FobKeypadSettings | None = Field(default=None, alias="keypadSettings")
    arm_control_settings: FobArmControlSettings | None = Field(
        default=None, alias="armControlSettings"
    )
    # Spec-documented fob fields (Protect 7.3.70)
    fob_type: str | None = Field(default=None, alias="fobType")
    associated_user_id: str | None = Field(default=None, alias="associatedUserId")
    is_paired: bool | None = Field(default=None, alias="isPaired")
    panic_button_mode: str | None = Field(default=None, alias="panicButtonMode")
    assigned_zones: list[Any] | None = Field(default=None, alias="assignedZones")

    model_config = {"populate_by_name": True, "extra": "allow"}

    @property
    def display_name(self) -> str:
        """Return display name for the fob."""
        return self.name or self.mac or self.id


Fob = KeypadFob
