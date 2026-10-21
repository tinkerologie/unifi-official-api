"""UniFi Protect Sensor model."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SensorType(StrEnum):
    """Types of UniFi sensors."""

    DOOR = "door"
    WINDOW = "window"
    MOTION = "motion"
    WATER = "water"
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    LIGHT = "light"
    UNKNOWN = "unknown"


class BatteryStatus(BaseModel):
    """Battery status for Protect sensors."""

    percentage: int | None = None
    is_low: bool = Field(default=False, alias="isLow")

    model_config = {"populate_by_name": True, "extra": "allow"}


class MotionSettings(BaseModel):
    """Motion sensor sensitivity settings returned by Protect."""

    sensitivity: float | None = None
    sensitivity_when_armed: float | None = Field(default=None, alias="sensitivityWhenArmed")

    model_config = {"populate_by_name": True, "extra": "allow"}


class SensorLedSettings(BaseModel):
    """LED settings for Protect sensor."""

    is_enabled: bool = Field(default=True, alias="isEnabled")

    model_config = {"populate_by_name": True, "extra": "allow"}


class Sensor(BaseModel):
    """
    UniFi Protect Sensor device.

    Represents Protect UP-Sense sensors.
    """

    id: str
    name: str | None = None
    mac: str
    model_key: str = Field(default="sensor", alias="modelKey")
    type: str | None = None
    model: str | None = None
    state: str | None = None
    firmware_version: str | None = Field(default=None, alias="firmwareVersion")
    hardware_revision: str | None = Field(default=None, alias="hardwareRevision")
    uptime: int | None = None
    last_seen: datetime | None = Field(default=None, alias="lastSeen")
    connected_since: datetime | None = Field(default=None, alias="connectedSince")
    is_connected: bool = Field(default=False, alias="isConnected")
    battery_status: BatteryStatus | None = Field(default=None, alias="batteryStatus")
    battery_level: int | None = Field(default=None, alias="batteryLevel")
    is_opened: bool | None = Field(default=None, alias="isOpened")
    open_status_changed_at: int | None = Field(default=None, alias="openStatusChangedAt")
    is_motion_detected: bool | None = Field(default=None, alias="isMotionDetected")
    motion_detected_at: int | None = Field(default=None, alias="motionDetectedAt")
    is_alarm_detected: bool | None = Field(default=None, alias="isAlarmDetected")
    temperature: float | None = None
    humidity: float | None = None
    light_value: float | None = Field(default=None, alias="lightValue")
    motion_sensitivity: int | None = Field(default=None, alias="motionSensitivity")
    motion_settings: MotionSettings | None = Field(default=None, alias="motionSettings")
    open_status_led_enabled: bool = Field(default=True, alias="openStatusLedEnabled")
    alarm_settings: dict[str, Any] | None = Field(default=None, alias="alarmSettings")
    mount_type: str | None = Field(default=None, alias="mountType")

    model_config = {"populate_by_name": True, "extra": "allow"}

    @field_validator("open_status_changed_at", "motion_detected_at", mode="before")
    @classmethod
    def _coerce_epoch_millis(cls, value: Any) -> int | None:
        """Coerce a timestamp payload to an integer epoch-millisecond value."""
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, datetime):
            dt = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
            return int(dt.timestamp() * 1000)
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value)
            except ValueError:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return int(dt.timestamp() * 1000)
        return None

    @property
    def display_name(self) -> str:
        """Get the display name for the sensor."""
        return self.name or self.mac
