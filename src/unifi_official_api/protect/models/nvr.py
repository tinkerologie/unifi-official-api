"""NVR models for UniFi Protect API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    Field,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    model_serializer,
)


class StorageInfo(BaseModel):
    """NVR storage information."""

    total_size: int = Field(default=0, alias="totalSize", strict=True)
    used_size: int = Field(default=0, alias="usedSize", strict=True)
    available_size: int = Field(default=0, alias="availableSize", strict=True)
    device_type: str | None = Field(default=None, alias="deviceType")
    healthy: bool | None = Field(default=None, strict=True)

    model_config = {"populate_by_name": True, "extra": "allow"}

    @property
    def usage_percent(self) -> float:
        """Calculate storage usage percentage."""
        if self.total_size == 0:
            return 0.0
        return (self.used_size / self.total_size) * 100


class NVR(BaseModel):
    """Model representing a UniFi Protect NVR."""

    id: str
    mac: str | None = None
    name: str | None = None
    type: str | None = None
    model: str | None = None
    host_type: str | None = Field(default=None, alias="hostType")
    firmware_version: str | None = Field(default=None, alias="firmwareVersion")
    hardware_revision: str | None = Field(default=None, alias="hardwareRevision")
    uptime: int | None = None
    last_seen: datetime | None = Field(default=None, alias="lastSeen")
    host: str | None = None
    version: str | None = None
    is_connected_to_cloud: bool = Field(default=False, alias="isConnectedToCloud")
    is_setup: bool = Field(default=False, alias="isSetup")
    is_recording_disabled: bool = Field(default=False, alias="isRecordingDisabled")
    is_recording_motion_only: bool = Field(default=False, alias="isRecordingMotionOnly")
    storage_info: StorageInfo | dict[str, Any] | None = Field(default=None, alias="storageInfo")
    timezone: str | None = None
    cpu_load: float | None = Field(default=None, alias="cpuLoad")
    memory_usage: float | None = Field(default=None, alias="memoryUsage")
    camera_count: int = Field(default=0, alias="cameraCount")
    recording_retention_days: int | None = Field(default=None, alias="recordingRetentionDays")
    enable_automatic_backups: bool = Field(default=False, alias="enableAutomaticBackups")
    feature_flags: dict[str, Any] | None = Field(default=None, alias="featureFlags")
    # Alarm Manager state (status, armProfileId, ...). Absent on firmware that
    # predates the Alarm Manager API, which reads as None.
    arm_mode: dict[str, Any] | None = Field(default=None, alias="armMode")

    model_config = {"populate_by_name": True, "extra": "allow"}

    @model_serializer(mode="wrap")
    def _serialize_storage(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> dict[str, Any]:
        """Keep omitted StorageInfo defaults out of coordinator telemetry."""
        result: dict[str, Any] = handler(self)
        if isinstance(self.storage_info, StorageInfo):
            key = "storageInfo" if info.by_alias else "storage_info"
            if key in result:
                supplied = self.storage_info.model_dump(by_alias=info.by_alias, exclude_unset=True)
                # Keep the handler's filtered values (including nested extras),
                # so include/exclude and exclude_none still apply to callers.
                result[key] = {
                    field: value for field, value in result[key].items() if field in supplied
                }
        return result

    @property
    def display_name(self) -> str:
        """Get the display name for the NVR."""
        return self.name or self.mac or self.id
