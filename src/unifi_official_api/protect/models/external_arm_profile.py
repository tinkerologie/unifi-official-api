"""External alarm manager arm profile model for UniFi Protect API."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import StrEnum
from typing import Any, Literal, Self, TypedDict, Unpack

from pydantic import (
    BaseModel,
    Field,
    SerializerFunctionWrapHandler,
    ValidationError,
    model_serializer,
    model_validator,
)

# Normalised key names that must never reach the model. Comparison happens after
# lower-casing and removing underscores, so ``pin_code``, ``pinCode`` and
# ``PIN`` all match, while ``has_pin`` (``haspin``) does not.
_PIN_KEY_NAMES = frozenset({"pin", "pincode", "pincodes"})


class _ValidationOptions(TypedDict, total=False):
    """Options shared by Pydantic's Python and JSON validation methods."""

    strict: bool | None
    extra: Literal["allow", "ignore", "forbid"] | None
    context: Any | None
    by_alias: bool | None
    by_name: bool | None


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
    if isinstance(value, Mapping):
        return {
            key: _strip_pin_keys(item)
            for key, item in value.items()
            if _normalised_key(key) not in _PIN_KEY_NAMES
        }
    if isinstance(value, list):
        return [_strip_pin_keys(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_strip_pin_keys(item) for item in value)
    if isinstance(value, frozenset):
        return frozenset(_strip_pin_keys(item) for item in value)
    if isinstance(value, set):
        return {_strip_pin_keys(item) for item in value}
    return value


def _sanitized_validation_error(model: type[BaseModel], err: ValidationError) -> ValidationError:
    """Return a ``ValidationError`` that quotes no input values.

    The rejected input is replaced with ``None`` in every error detail, so a
    PIN carried by a malformed body cannot surface in the message, ``repr`` or
    ``errors()`` payload of the replacement error.
    """
    details: list[Any] = []
    for item in err.errors(include_input=False, include_url=False):
        detail: dict[str, Any] = {
            "type": item["type"],
            "loc": item["loc"],
            "msg": item["msg"],
            "input": None,
        }
        if "ctx" in item:
            detail["ctx"] = item["ctx"]
        details.append(detail)
    return ValidationError.from_exception_data(model.__name__, details)


class ExternalArmProfile(BaseModel):
    """
    UniFi Protect arm profile owned by the external alarm manager.

    The response carries ``has_pin`` and never the PIN itself. ``extra="allow"``
    keeps the model forward-compatible, so the model keeps PIN-spelling keys
    (normalised ``pin``, ``pincode`` or ``pincodes``) out of every entry path:
    a before-validator strips them from nested mappings, lists, tuples and sets
    before validation, assignment and ``model_copy()`` drop them, and the
    serializer and ``__repr_args__`` filter them again, so no ``repr``, string
    form or dump can disclose one. Validation errors are re-raised without the
    rejected input for the same reason. ``pin_code`` stays write-only, as an
    endpoint parameter.
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

    @classmethod
    def model_validate(
        cls,
        obj: Any,
        *,
        from_attributes: bool | None = None,
        **kwargs: Unpack[_ValidationOptions],
    ) -> Self:
        """Validate one payload, raising errors that quote no input values."""
        try:
            return super().model_validate(obj, from_attributes=from_attributes, **kwargs)
        except ValidationError as err:
            sanitized = _sanitized_validation_error(cls, err)
        # Raised after the handler so neither __cause__ nor __context__ points
        # at the rejected input.
        raise sanitized from None

    @classmethod
    def model_validate_json(
        cls,
        json_data: str | bytes | bytearray,
        **kwargs: Unpack[_ValidationOptions],
    ) -> Self:
        """Validate one JSON payload, raising errors that quote no input values."""
        try:
            return super().model_validate_json(json_data, **kwargs)
        except ValidationError as err:
            sanitized = _sanitized_validation_error(cls, err)
        # Raised after the handler so neither __cause__ nor __context__ points
        # at the rejected input.
        raise sanitized from None

    def model_copy(self, *, update: Mapping[str, Any] | None = None, deep: bool = False) -> Self:
        """Return a copy with PIN-spelling keys removed from the update."""
        cleaned = (
            None
            if update is None
            else {
                name: _strip_pin_keys(value)
                for name, value in update.items()
                if _normalised_key(name) not in _PIN_KEY_NAMES
            }
        )
        return super().model_copy(update=cleaned, deep=deep)

    def __setattr__(self, name: str, value: Any) -> None:
        """Store a value, dropping PIN-spelling attributes instead."""
        if _normalised_key(name) in _PIN_KEY_NAMES:
            return
        super().__setattr__(name, _strip_pin_keys(value))

    def __repr_args__(self) -> Iterable[tuple[str | None, Any]]:
        """Return representation pairs with PIN-spelling keys and values removed."""
        return [
            (name, _strip_pin_keys(value))
            for name, value in super().__repr_args__()
            if _normalised_key(name) not in _PIN_KEY_NAMES
        ]

    @model_serializer(mode="wrap")
    def _serialize_without_pins(self, handler: SerializerFunctionWrapHandler) -> Any:
        """Remove PIN-spelling keys from every dump, including extras and nesting."""
        return _strip_pin_keys(handler(self))
