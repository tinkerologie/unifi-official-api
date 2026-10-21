"""Alarm hub endpoint for UniFi Protect API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from ...validation import require_record, written_record
from ..models import AlarmHub

if TYPE_CHECKING:
    from ..client import UniFiProtectClient

_LOGGER = logging.getLogger(__name__)


class AlarmHubsEndpoint:
    """Endpoint for managing UniFi Protect alarm hubs."""

    def __init__(self, client: UniFiProtectClient) -> None:
        """
        Initialize the alarm hubs endpoint.

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
    ) -> list[AlarmHub]:
        """
        List all alarm hubs.

        Args:
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).
            expected_unsupported: Whether a non-JSON 2xx response is an
                expected unsupported-endpoint signal - a Protect version
                without this endpoint serving its web page. Only lowers the
                log level of an unredirected response; the call still raises.

        Returns:
            List of alarm hubs.

        """
        path = self._client.build_api_path("/alarm-hubs", site_id)
        self.last_result_complete = True
        response = await self._client._get(path, expected_unsupported=expected_unsupported)

        if response is None:
            return []

        data = response.get("data", response) if isinstance(response, dict) else response
        if not isinstance(data, list):
            return []

        hubs: list[AlarmHub] = []
        for item in data:
            try:
                hubs.append(AlarmHub.model_validate(item))
            except ValidationError as err:
                self.last_result_complete = False
                _LOGGER.warning(
                    "Skipping alarm hub that failed to parse (id=%s): %s",
                    item.get("id") if isinstance(item, dict) else "?",
                    err,
                )
        return hubs

    async def get(self, alarm_hub_id: str, site_id: str | None = None) -> AlarmHub:
        """
        Get a specific alarm hub.

        Args:
            alarm_hub_id: The alarm hub ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The alarm hub.

        Raises:
            UniFiNotFoundError: If the response holds no alarm hub with an ``id``.
            UniFiResponseError: If the alarm hub in the response fails validation.

        """
        path = self._client.build_api_path(f"/alarm-hubs/{alarm_hub_id}", site_id)
        return require_record(await self._client._get(path), AlarmHub, f"Alarm hub {alarm_hub_id}")

    async def update(
        self,
        alarm_hub_id: str,
        site_id: str | None = None,
        **kwargs: Any,
    ) -> AlarmHub:
        """
        Update alarm hub settings.

        Args:
            alarm_hub_id: The alarm hub ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).
            **kwargs: Settings to update.

        Returns:
            The updated alarm hub.

        Raises:
            TypeError: If ``site_id`` is neither a string nor ``None``.
            UniFiNotFoundError: If the follow-up ``get()`` finds no alarm hub.
            UniFiResponseError: If the follow-up ``get()`` response fails validation.

        """
        if site_id is not None and not isinstance(site_id, str):
            msg = (
                f"site_id must be a str or None, not {type(site_id).__name__}; "
                "pass settings as keyword arguments"
            )
            raise TypeError(msg)
        path = self._client.build_api_path(f"/alarm-hubs/{alarm_hub_id}", site_id)
        written = written_record(await self._client._patch(path, json_data=kwargs), AlarmHub)
        if written is not None:
            return written
        return await self.get(alarm_hub_id, site_id)

    async def trigger_output(
        self,
        alarm_hub_id: str,
        output_id: str,
        site_id: str | None = None,
        **kwargs: Any,
    ) -> bool:
        """
        Trigger an alarm hub output.

        Args:
            alarm_hub_id: The alarm hub ID.
            output_id: The output ID to trigger.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).
            **kwargs: Optional trigger payload fields.

        Returns:
            True if the request was accepted.

        """
        path = self._client.build_api_path(
            f"/alarm-hubs/{alarm_hub_id}/outputs/{output_id}/trigger", site_id
        )
        await self._client._post(path, json_data=kwargs or None)
        return True
