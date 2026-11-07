"""Users endpoint for UniFi Protect API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ...validation import require_record
from ..models.user import ProtectUser, User
from ._listing import ProtectListResult, parse_listing

if TYPE_CHECKING:
    from ..client import UniFiProtectClient

_LOGGER = logging.getLogger(__name__)


class UsersEndpoint:
    """Endpoint for UniFi Protect users."""

    def __init__(self, client: UniFiProtectClient) -> None:
        """Initialize the users endpoint."""
        self._client = client
        self.last_result_complete: bool = True

    async def get_all(
        self,
        site_id: str | None = None,
        *,
        expected_unsupported: bool = False,
    ) -> list[User]:
        """
        Get all Protect users.

        Args:
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).
            expected_unsupported: Whether a non-JSON 2xx response is expected.

        Returns:
            List of Protect users.

        """
        path = self._client.build_api_path("/users", site_id)
        self.last_result_complete = True
        response = await self._client._get(path, expected_unsupported=expected_unsupported)
        return list(parse_listing(User, response, "user", _LOGGER, legacy_state=self).records)

    async def get_all_result(
        self, site_id: str | None = None, *, expected_unsupported: bool = False
    ) -> ProtectListResult[User]:
        """Return parsed records and completeness from this request."""
        path = self._client.build_api_path("/users", site_id)
        response = await self._client._get(path, expected_unsupported=expected_unsupported)
        return parse_listing(User, response, "user", _LOGGER)

    async def get(self, user_id: str, site_id: str | None = None) -> User:
        """
        Get a specific Protect user by ID.

        Args:
            user_id: The primary key of the user.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The Protect user.

        Raises:
            ValueError: If ``user_id`` is empty; no request is made.
            UniFiNotFoundError: If the response holds no user with an ``id``.
            UniFiResponseError: If the user in the response fails validation.

        """
        if not isinstance(user_id, str) or not user_id.strip():
            msg = "User ID must be a non-empty string"
            raise ValueError(msg)

        path = self._client.build_api_path(f"/users/{user_id}", site_id)
        return require_record(await self._client._get(path), User, f"User {user_id}")

    # Backwards compatibility methods
    async def get_users(self, site_id: str | None = None) -> list[ProtectUser]:
        """List all protect users (alias for get_all)."""
        return await self.get_all(site_id=site_id)

    async def get_user(self, user_id: str, site_id: str | None = None) -> ProtectUser:
        """Get a single protect user (alias for get)."""
        return await self.get(user_id=user_id, site_id=site_id)


__all__ = ["UsersEndpoint"]
