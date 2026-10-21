"""Link station and alarm hub models for UniFi Protect API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LinkStationThreadNetwork(BaseModel):
    """
    Thread mesh status reported by a Thread-capable gateway (Protect 7.3.70+).

    Every field is optional and unconstrained on purpose: the endpoint drops a
    whole device on a ValidationError, so a new firmware enum value (a new
    Thread role, say) must parse rather than make the gateway vanish.
    """

    status: str | None = None  # "ready" | "error"
    role: str | None = None  # disabled | detached | child | router | leader
    network_name: str | None = Field(default=None, alias="networkName")
    channel: int | None = None  # 11-26 per spec
    pan_id: str | None = Field(default=None, alias="panId")
    extended_pan_id: str | None = Field(default=None, alias="extendedPanId")
    joined_device_count: int | None = Field(default=None, alias="joinedDeviceCount")
    error_reason: str | None = Field(default=None, alias="errorReason")
    last_updated_at: float | None = Field(default=None, alias="lastUpdatedAt")

    model_config = {"populate_by_name": True, "extra": "allow"}


class LinkStationThreadState(BaseModel):
    """Thread state wrapper; network is null on SKUs without Thread."""

    network: LinkStationThreadNetwork | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class LinkStation(BaseModel):
    """UniFi Protect link station or alarm hub (modelKey='linkStation')."""

    id: str
    mac: str | None = None
    name: str | None = None
    type: str | None = None
    model: str | None = None
    model_key: str | None = Field(default="linkStation", alias="modelKey")
    state: str | None = None
    firmware_version: str | None = Field(default=None, alias="firmwareVersion")
    hardware_revision: str | None = Field(default=None, alias="hardwareRevision")
    uptime: int | None = None
    last_seen: datetime | None = Field(default=None, alias="lastSeen")
    connected_since: datetime | None = Field(default=None, alias="connectedSince")
    is_connected: bool = Field(default=False, alias="isConnected")
    is_alarm_hub: bool | None = Field(default=None, alias="isAlarmHub")
    connection_type: str | None = Field(default=None, alias="connectionType")
    bridge: str | None = None
    led_settings: dict[str, Any] | None = Field(default=None, alias="ledSettings")
    alarm_hub: dict[str, Any] | None = Field(default=None, alias="alarmHub")
    thread_state: LinkStationThreadState | None = Field(default=None, alias="threadState")
    last_event: int | float | dict[str, Any] | None = Field(default=None, alias="lastEvent")
    inputs: list[dict[str, Any]] | None = None
    outputs: list[dict[str, Any]] | None = None
    zones: list[dict[str, Any]] | None = None
    ble_clients: int | None = Field(default=None, alias="bleClients")
    sub_ghz_clients: int | None = Field(default=None, alias="subGhzClients")
    sub_ghz_tx_power_mode: str | None = Field(default=None, alias="subGhzTxPowerMode")
    status_led_enabled: bool | None = Field(default=None, alias="statusLedEnabled")
    tamper_state: str | None = Field(default=None, alias="tamperState")
    tamper_enabled: bool | None = Field(default=None, alias="tamperEnabled")

    model_config = {"populate_by_name": True, "extra": "allow"}

    @property
    def display_name(self) -> str:
        """Return display name for the link station."""
        return self.name or self.mac or self.id


AlarmHub = LinkStation
