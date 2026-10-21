"""LiveViews endpoint for UniFi Protect API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...validation import created_record, require_record, written_record
from ..models import LiveView

if TYPE_CHECKING:
    from ..client import UniFiProtectClient


class LiveViewsEndpoint:
    """Endpoint for managing UniFi Protect live views."""

    def __init__(self, client: UniFiProtectClient) -> None:
        """
        Initialize the live views endpoint.

        Args:
            client: The UniFi Protect client.

        """
        self._client = client

    async def get_all(self, site_id: str | None = None) -> list[LiveView]:
        """
        List all live views.

        Args:
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            List of live views.

        """
        path = self._client.build_api_path("/liveviews", site_id)
        response = await self._client._get(path)

        if response is None:
            return []

        data = response.get("data", response) if isinstance(response, dict) else response
        if isinstance(data, list):
            return [LiveView.model_validate(item) for item in data]
        return []

    async def get(self, liveview_id: str, site_id: str | None = None) -> LiveView:
        """
        Get a specific live view.

        Args:
            liveview_id: The live view ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The live view.

        Raises:
            UniFiNotFoundError: If the response holds no live view with an ``id``.
            UniFiResponseError: If the live view in the response fails validation.

        """
        path = self._client.build_api_path(f"/liveviews/{liveview_id}", site_id)
        return require_record(await self._client._get(path), LiveView, f"LiveView {liveview_id}")

    async def create(
        self,
        *,
        name: str,
        layout: int = 1,
        slots: list[dict[str, Any]] | None = None,
        site_id: str | None = None,
        **kwargs: Any,
    ) -> LiveView:
        """
        Create a new live view.

        Args:
            name: Name of the live view.
            layout: Layout grid size (1, 4, 9, 16).
            slots: List of slot configurations.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).
            **kwargs: Additional parameters.

        Returns:
            The created live view.

        Raises:
            UniFiResponseError: If the console accepted the request but the response
                holds no valid live view. The live view may have been created.

        """
        path = self._client.build_api_path("/liveviews", site_id)
        data: dict[str, Any] = {
            "name": name,
            "layout": layout,
        }
        if slots is not None:
            data["slots"] = slots
        data.update(kwargs)

        response = await self._client._post(path, json_data=data)
        return created_record(response, LiveView, f"Live view {name}")

    async def update(
        self,
        liveview_id: str,
        site_id: str | None = None,
        **kwargs: Any,
    ) -> LiveView:
        """
        Update a live view.

        Args:
            liveview_id: The live view ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).
            **kwargs: Parameters to update.

        Returns:
            The updated live view.

        Raises:
            UniFiNotFoundError: If the follow-up ``get()`` finds no live view.
            UniFiResponseError: If the follow-up ``get()`` response fails validation.

        """
        path = self._client.build_api_path(f"/liveviews/{liveview_id}", site_id)
        written = written_record(await self._client._patch(path, json_data=kwargs), LiveView)
        if written is not None:
            return written
        return await self.get(liveview_id, site_id)
