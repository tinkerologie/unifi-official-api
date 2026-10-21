"""Door models for the UniFi Access developer API."""

from typing import Any, Literal

from pydantic import field_validator

from .common import AccessRecord, known_or_none

# Documented enum: door_lock_relay_status {lock,unlock}.
DoorLockRelayStatus = Literal["lock", "unlock"]
DOOR_LOCK_RELAY_STATUSES: tuple[DoorLockRelayStatus, ...] = ("lock", "unlock")
# Documented door position values; an empty string or null means no sensor.
DoorPositionStatus = Literal["open", "close"]
DOOR_POSITION_STATUSES: tuple[DoorPositionStatus, ...] = ("open", "close")


class AccessDoor(AccessRecord):
    """
    One Access door, as returned by ``GET /doors`` and ``GET /doors/:id``.

    Verified against the Ubiquiti UniFi Access API Reference V2.2.10
    (Sections 7.5 and 7.6). The documented schema has no list of associated
    devices. A door is linked to its hub only through ``is_bind_hub``, and to
    readers only through device fields in :class:`AccessDevice`.
    """

    id: str | None = None
    name: str | None = None
    full_name: str | None = None
    floor_id: str | None = None
    type: str | None = None
    is_bind_hub: bool | None = None
    door_lock_relay_status: DoorLockRelayStatus | None = None
    door_position_status: DoorPositionStatus | None = None

    @field_validator("door_lock_relay_status", mode="before")
    @classmethod
    def _lock_status(cls, value: Any) -> DoorLockRelayStatus | None:
        """Keep only documented relay states; anything else is unknown."""
        return known_or_none(value, DOOR_LOCK_RELAY_STATUSES)

    @field_validator("door_position_status", mode="before")
    @classmethod
    def _position_status(cls, value: Any) -> DoorPositionStatus | None:
        """Map the documented open/close values; "" and unknown values are unknown."""
        return known_or_none(value, DOOR_POSITION_STATUSES)
