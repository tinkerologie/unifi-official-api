"""Chimes endpoint for UniFi Protect API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from ...exceptions import UniFiResponseError, UniFiUnsupportedError, UniFiValidationError
from ...validation import require_record, written_record
from ..models import Chime

if TYPE_CHECKING:
    from ..client import UniFiProtectClient

_LOGGER = logging.getLogger(__name__)

# Fields of one ringSettings entry. The v7.3.70 chime PATCH requires all four
# and rejects any other key.
_RING_SETTINGS_FIELDS = ("cameraId", "repeatTimes", "ringtoneId", "volume")


class ChimesEndpoint:
    """Endpoint for managing UniFi Protect chimes."""

    def __init__(self, client: UniFiProtectClient) -> None:
        """
        Initialize the chimes endpoint.

        Args:
            client: The UniFi Protect client.

        """
        self._client = client
        # False when the most recent get_all() silently dropped an item on a
        # ValidationError. Callers need to tell a complete listing from a short
        # one: a device absent because its payload would not parse is still
        # adopted, and must not be treated as removed.
        self.last_result_complete: bool = True

    async def get_all(
        self,
        site_id: str | None = None,
        *,
        expected_unsupported: bool = False,
    ) -> list[Chime]:
        """
        List all chimes.

        Args:
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).
            expected_unsupported: Whether a non-JSON 2xx response is an expected unsupported signal.

        Returns:
            List of chimes.

        """
        path = self._client.build_api_path("/chimes", site_id)
        self.last_result_complete = True
        response = await self._client._get(path, expected_unsupported=expected_unsupported)

        if response is None:
            return []

        data = response.get("data", response) if isinstance(response, dict) else response
        if not isinstance(data, list):
            return []

        chimes: list[Chime] = []
        for item in data:
            try:
                chimes.append(Chime.model_validate(item))
            except ValidationError as err:
                self.last_result_complete = False
                _LOGGER.warning(
                    "Skipping chime that failed to parse (id=%s): %s",
                    item.get("id") if isinstance(item, dict) else "?",
                    err,
                )
        return chimes

    async def get(self, chime_id: str, site_id: str | None = None) -> Chime:
        """
        Get a specific chime.

        Args:
            chime_id: The chime ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The chime.

        Raises:
            UniFiNotFoundError: If the response holds no chime with an ``id``.
            UniFiResponseError: If the chime in the response fails validation.

        """
        path = self._client.build_api_path(f"/chimes/{chime_id}", site_id)
        return require_record(await self._client._get(path), Chime, f"Chime {chime_id}")

    async def update(
        self,
        chime_id: str,
        site_id: str | None = None,
        **kwargs: Any,
    ) -> Chime:
        """
        Update chime settings.

        Args:
            chime_id: The chime ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).
            **kwargs: Settings to update.

        Returns:
            The updated chime.

        Raises:
            UniFiNotFoundError: If the follow-up ``get()`` finds no chime.
            UniFiResponseError: If the follow-up ``get()`` response fails validation.

        """
        path = self._client.build_api_path(f"/chimes/{chime_id}", site_id)
        written = written_record(await self._client._patch(path, json_data=kwargs), Chime)
        if written is not None:
            return written
        return await self.get(chime_id, site_id)

    async def _update_ring_settings(
        self,
        chime_id: str,
        site_id: str | None,
        **changes: Any,
    ) -> Chime:
        """
        Change fields in every ringSettings entry of a chime.

        The chime PATCH body has no top-level volume, ringtone or repeat
        count: they are set per paired doorbell in ``ringSettings``. This
        reads the chime's current ring settings and sends them back with
        ``changes`` applied to each entry.

        Raises:
            UniFiValidationError: If the chime has no paired doorbell to apply the
                settings to; no write is made.
            UniFiResponseError: If an entry lacks a field that isn't being changed.
            UniFiNotFoundError: If the chime read finds no chime.

        """
        chime = await self.get(chime_id, site_id)
        entries = (chime.model_extra or {}).get("ringSettings")
        if not entries:
            msg = f"Chime {chime_id} has no paired doorbell to apply ring settings to"
            raise UniFiValidationError(msg)
        kept = [key for key in _RING_SETTINGS_FIELDS if key not in changes]
        if not isinstance(entries, list) or not all(
            isinstance(entry, dict) and all(key in entry for key in kept) for entry in entries
        ):
            msg = f"Chime {chime_id} response has incomplete ring settings"
            raise UniFiResponseError(msg, status_code=200)
        ring_settings = [{key: entry[key] for key in kept} | changes for entry in entries]
        return await self.update(chime_id, site_id, ringSettings=ring_settings)

    async def set_volume(
        self,
        chime_id: str,
        volume: int,
        site_id: str | None = None,
    ) -> Chime:
        """
        Set chime volume for every paired doorbell.

        Args:
            chime_id: The chime ID.
            volume: Volume level (0-100).
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The updated chime.

        Raises:
            ValueError: If the volume is out of range; no request is made.
            UniFiValidationError: If the chime has no paired doorbell to apply it to.
            UniFiResponseError: If an entry lacks a field that isn't being changed.

        """
        if not 0 <= volume <= 100:
            raise ValueError("Volume must be between 0 and 100")
        return await self._update_ring_settings(chime_id, site_id, volume=volume)

    async def set_repeat_times(
        self,
        chime_id: str,
        repeat_times: int,
        site_id: str | None = None,
    ) -> Chime:
        """
        Set how many times the ringtone repeats, for every paired doorbell.

        Args:
            chime_id: The chime ID.
            repeat_times: Repeat count (1-10).
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The updated chime.

        Raises:
            ValueError: If the count is out of range; no request is made.
            UniFiValidationError: If the chime has no paired doorbell to apply it to.
            UniFiResponseError: If an entry lacks a field that isn't being changed.

        """
        if not 1 <= repeat_times <= 10:
            raise ValueError("Repeat times must be between 1 and 10")
        return await self._update_ring_settings(chime_id, site_id, repeatTimes=repeat_times)

    async def set_ringtone(
        self,
        chime_id: str,
        ringtone_id: str,
        site_id: str | None = None,
    ) -> Chime:
        """
        Set the ringtone ID for every paired doorbell.

        The official API does not enumerate ringtones. IDs are opaque strings,
        and the console validates whether a ringtone exists.

        Raises:
            ValueError: If the ID is empty; no request is made.
            UniFiValidationError: If the chime has no paired doorbell to apply it to.
            UniFiResponseError: If an entry lacks a field that isn't being changed.

        """
        if not isinstance(ringtone_id, str) or not ringtone_id.strip():
            msg = "Ringtone ID must be a non-empty string"
            raise ValueError(msg)
        return await self._update_ring_settings(chime_id, site_id, ringtoneId=ringtone_id.strip())

    async def play(self, chime_id: str, site_id: str | None = None) -> bool:
        """
        Report that chime playback is unsupported, without making a request.

        Protect v7.3.70 has no chime playback route. A live request to the
        undocumented route returns 404 "endpoint not found".

        Args:
            chime_id: The chime ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Raises:
            UniFiUnsupportedError: The official API cannot play a chime.

        """
        del chime_id, site_id
        msg = "The official Protect API does not support chime playback"
        raise UniFiUnsupportedError(msg)
