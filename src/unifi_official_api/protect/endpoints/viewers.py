"""Viewers endpoint for UniFi Protect API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from ...validation import require_record, written_record
from ..models.viewer import Viewer

if TYPE_CHECKING:
    from ..client import UniFiProtectClient

_LOGGER = logging.getLogger(__name__)


class ViewersEndpoint:
    """Endpoint for managing UniFi Protect viewers."""

    def __init__(self, client: UniFiProtectClient) -> None:
        """
        Initialize the viewers endpoint.

        Args:
            client: The UniFi Protect client.

        """
        self._client = client
        # False when the most recent get_all() silently dropped an item on a
        # ValidationError. Callers need to tell a complete listing from a short
        # one: a device absent because its payload would not parse is still
        # adopted, and must not be treated as removed.
        self.last_result_complete: bool = True

    async def get_all(self, site_id: str | None = None) -> list[Viewer]:
        """
        List all viewers.

        Args:
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            List of viewers.

        """
        path = self._client.build_api_path("/viewers", site_id)
        self.last_result_complete = True
        response = await self._client._get(path)

        if response is None:
            return []

        data = response.get("data", response) if isinstance(response, dict) else response
        if not isinstance(data, list):
            return []

        viewers: list[Viewer] = []
        for item in data:
            try:
                viewers.append(Viewer.model_validate(item))
            except ValidationError as err:
                self.last_result_complete = False
                _LOGGER.warning(
                    "Skipping viewer that failed to parse (id=%s): %s",
                    item.get("id") if isinstance(item, dict) else "?",
                    err,
                )
        return viewers

    async def get(self, viewer_id: str, site_id: str | None = None) -> Viewer:
        """
        Get a specific viewer.

        Args:
            viewer_id: The viewer ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The viewer.

        Raises:
            UniFiNotFoundError: If the response holds no viewer with an ``id``.
            UniFiResponseError: If the viewer in the response fails validation.

        """
        path = self._client.build_api_path(f"/viewers/{viewer_id}", site_id)
        return require_record(await self._client._get(path), Viewer, f"Viewer {viewer_id}")

    async def update(
        self,
        viewer_id: str,
        site_id: str | None = None,
        **kwargs: Any,
    ) -> Viewer:
        """
        Update viewer settings.

        Args:
            viewer_id: The viewer ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).
            **kwargs: Settings to update (name, liveview).

        Returns:
            The updated viewer.

        Raises:
            UniFiNotFoundError: If the follow-up ``get()`` finds no viewer.
            UniFiResponseError: If the follow-up ``get()`` response fails validation.

        """
        path = self._client.build_api_path(f"/viewers/{viewer_id}", site_id)
        written = written_record(await self._client._patch(path, json_data=kwargs), Viewer)
        if written is not None:
            return written
        return await self.get(viewer_id, site_id)

    async def set_liveview(
        self,
        viewer_id: str,
        liveview_id: str | None,
        site_id: str | None = None,
    ) -> Viewer:
        """
        Set the liveview for a viewer.

        Args:
            viewer_id: The viewer ID.
            liveview_id: The liveview ID or None to unset.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The updated viewer.

        """
        return await self.update(viewer_id, site_id, liveview=liveview_id)
