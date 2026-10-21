"""User models for the UniFi Access developer API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import SecretStr, field_validator

from .common import AccessRecord, known_or_none

# Documented user status values. PENDING is read-only: it can be returned but
# not written, so writes accept only the two values below.
AccessUserStatus = Literal["ACTIVE", "PENDING", "DEACTIVATED"]
ACCESS_USER_STATUSES: tuple[AccessUserStatus, ...] = (
    "ACTIVE",
    "PENDING",
    "DEACTIVATED",
)
WRITABLE_USER_STATUSES: tuple[Literal["ACTIVE", "DEACTIVATED"], ...] = (
    "ACTIVE",
    "DEACTIVATED",
)


class AccessPinCredential(AccessRecord):
    """PIN credential summary. The token is a hash and is never shown in reprs."""

    token: SecretStr | None = None


class AccessUser(AccessRecord):
    """
    One Access user, as documented on the user endpoints.

    Verified against the Ubiquiti UniFi Access API Reference V2.2.10
    (Sections 3.4 and 3.5, including ``pin_code.token`` and
    ``access_policy_ids``) and vendored test payloads.
    """

    id: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    alias: str | None = None
    user_email: str | None = None
    employee_number: str | None = None
    onboard_time: int | None = None
    status: AccessUserStatus | None = None
    pin_code: AccessPinCredential | None = None
    access_policy_ids: list[str] | None = None

    @field_validator("status", mode="before")
    @classmethod
    def _status(cls, value: Any) -> AccessUserStatus | None:
        """Keep only documented status values; anything else is unknown."""
        return known_or_none(value, ACCESS_USER_STATUSES)
