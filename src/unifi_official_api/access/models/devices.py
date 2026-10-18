"""Device models for the UniFi Access developer API."""

from __future__ import annotations

from typing import Any

from pydantic import field_validator

from .common import AccessRecord


def _blank_to_none(value: Any) -> Any:
    """Treat an empty string as an unknown value, not as a real identifier."""
    if isinstance(value, str) and not value.strip():
        return None
    return value


class AccessDevice(AccessRecord):
    """
    One Access device, as returned by ``GET /devices``.

    ``id``, ``name``, ``type``, and ``full_name`` match the Ubiquiti UniFi
    Access API Reference V2.2.10 (Section 8.1). ``type`` is the hardware model
    string, for example ``UAH`` for an Access hub, ``UGT`` for a gate hub, or
    ``UA-G2-PRO`` for a reader or intercom.

    ``location_id``, ``connected_uah_id``, ``is_online`` and ``alias`` are not
    in the V2.2.10 PDF reference for ``GET /devices``. They are third-party-derived
    (``pyua`` / ``hjdhjd/unifi-access``) and live-console fields. Every one stays
    ``None`` when the console omits it or sends an empty or non-boolean value.

    Door ownership: ``location_id`` is the only field that links a device to a
    door, and it is the only link used. Names and ``full_name`` are display text
    and are never matched against a door.
    """

    id: str | None = None
    name: str | None = None
    type: str | None = None
    full_name: str | None = None
    alias: str | None = None
    location_id: str | None = None
    connected_uah_id: str | None = None
    is_online: bool | None = None

    @field_validator("alias", "location_id", "connected_uah_id", mode="before")
    @classmethod
    def _text_or_none(cls, value: Any) -> Any:
        """Empty identifiers and aliases are unknown."""
        return _blank_to_none(value)

    @field_validator("is_online", mode="before")
    @classmethod
    def _online_or_none(cls, value: Any) -> Any:
        """Only a real boolean counts; a string or number is unknown, not online."""
        return value if isinstance(value, bool) else None
