"""External alarm manager arm profile model for UniFi Protect API."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator

# Normalised key names that must never reach the model. Comparison happens after
# lower-casing and removing underscores, so ``pin_code``, ``pinCode`` and
# ``PIN`` all match, while ``has_pin`` (``haspin``) does not.
_PIN_KEY_NAMES = frozenset({"pin", "pincode", "pincodes"})


class ExternalArmProfileState(StrEnum):
    """Arm state reported by the external alarm manager."""

    BREACHED = "breached"
    BREACHING = "breaching"
    ARMED = "armed"
    DISARMED = "disarmed"
    ARMING = "arming"


def _normalised_key(key: object) -> str:
    """Return a dictionary key as lower case without underscores."""
    return str(key).lower().replace("_", "")


def _strip_pin_keys(value: Any) -> Any:
    """Return ``value`` with every PIN-spelling key removed, recursively."""
    if isinstance(value, dict):
        return {
            key: _strip_pin_keys(item)
            for key, item in value.items()
            if _normalised_key(key) not in _PIN_KEY_NAMES
        }
    if isinstance(value, list):
        return [_strip_pin_keys(item) for item in value]
    return value


class ExternalArmProfile(BaseModel):
    """
    UniFi Protect arm profile owned by the external alarm manager.

    The response carries ``has_pin`` and never the PIN itself. ``extra="allow"``
    keeps the model forward-compatible, so a before-validator removes any key
    whose normalised name is ``pin``, ``pincode`` or ``pincodes`` from nested
    dictionaries and lists before validation: no entry path can put a PIN on
    the model, and no ``repr`` or dump can disclose one. ``pin_code`` stays
    write-only, as an endpoint parameter.
    """

    id: str
    title: str | None = None
    state: ExternalArmProfileState | str | None = Field(default=None, union_mode="left_to_right")
    state_set_at: str | None = None
    state_promotion_due_at: str | None = None
    created_at: str | None = None
    created_by: str | None = None
    updated_at: str | None = None
    updated_by: str | None = None
    activation_delay: int | float | None = None
    deactivation_delay: int | float | None = None
    active_breach_id: int | float | None = None
    alarm_ids: list[str] | None = None
    has_pin: bool | None = None
    schedule: dict[str, Any] | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}

    @model_validator(mode="before")
    @classmethod
    def _remove_pin_keys(cls, data: Any) -> Any:
        """Remove PIN-spelling keys from the payload before validation."""
        return _strip_pin_keys(data)
