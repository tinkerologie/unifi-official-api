"""User endpoints for the UniFi Access developer API: PIN codes and status."""

from typing import TYPE_CHECKING, Literal

from ...exceptions import UniFiValidationError
from ..errors import ensure_success_envelope
from .common import safe_id

if TYPE_CHECKING:
    from ..client import UniFiAccessClient

# The official API accepts only these two values on write. PENDING is read-only.
UserStatusWrite = Literal["ACTIVE", "DEACTIVATED"]
USER_STATUS_WRITES: tuple[UserStatusWrite, ...] = ("ACTIVE", "DEACTIVATED")


class UsersEndpoint:
    """
    Change a user's PIN and account status (``edit:user``).

    Verified against the Ubiquiti UniFi Access API Reference V2.2.10
    (Sections 3.2, 3.6, and 3.7) and live-console / vendored tests.
    PIN requests never log bodies: the PIN is a credential, and the response
    to a PIN request echoes nothing useful for diagnostics.
    """

    def __init__(self, client: UniFiAccessClient) -> None:
        """Initialize the endpoint group."""
        self._client = client

    async def set_pin(self, user_id: str, pin: str) -> None:
        """
        Assign a user-chosen PIN (``PUT users/:id/pin_codes``).

        The PIN must be digits only. The official PDF does not state a length
        range. The console rejects an invalid length with
        ``CODE_CREDS_PIN_CODE_CREDS_LENGTH_INVALID``, which surfaces as the
        ``api_error_code`` of the raised response error.
        """
        if not isinstance(pin, str) or not pin.isdigit() or not pin.isascii():
            msg = "PIN must contain digits only"
            raise UniFiValidationError(msg)
        path = f"users/{safe_id(user_id)}/pin_codes"
        response = await self._client._put(path, json_data={"pin_code": pin}, log_body=False)
        ensure_success_envelope(response, path)

    async def remove_pin(self, user_id: str) -> None:
        """Remove a user's PIN (``DELETE users/:id/pin_codes``)."""
        path = f"users/{safe_id(user_id)}/pin_codes"
        response = await self._client._delete(path, log_body=False)
        ensure_success_envelope(response, path)

    async def set_status(self, user_id: str, status: UserStatusWrite) -> None:
        """
        Set a user account to ACTIVE or DEACTIVATED (``PUT users/:id``).

        This controls the whole user account, not one credential. A deactivated
        user loses access through every credential.
        """
        if status not in USER_STATUS_WRITES:
            msg = "User status must be ACTIVE or DEACTIVATED"
            raise UniFiValidationError(msg)
        path = f"users/{safe_id(user_id)}"
        response = await self._client._put(path, json_data={"status": status}, log_body=False)
        ensure_success_envelope(response, path)
