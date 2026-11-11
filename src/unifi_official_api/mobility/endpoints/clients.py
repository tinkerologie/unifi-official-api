"""Clients endpoint for UniFi Mobility API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...validation import parse_records
from ..models.client import MobilityDeviceClient

if TYPE_CHECKING:
    from ..client import UniFiMobilityClient


class ClientsEndpoint:
    """Endpoint for inspecting connected clients on mobility devices."""

    def __init__(self, client: UniFiMobilityClient) -> None:
        """
        Initialize the clients endpoint.

        Args:
            client: The UniFi Mobility client.
        """
        self._client = client

    async def get_all(self, workspace_id: str, device_id: str) -> list[MobilityDeviceClient]:
        """
        Return one page of clients associated with a mobility device.

        Args:
            workspace_id: Workspace UUID.
            device_id: Device UUID.

        Returns:
            List of MobilityDeviceClient objects.

        Raises:
            UniFiResponseError: If an item in the response fails validation.
        """
        response = await self._client._get(
            self._client._device_clients_path(workspace_id, device_id)
        )
        if response is None:
            return []
        data = response.get("data", response) if isinstance(response, dict) else response
        if isinstance(data, list):
            return parse_records(MobilityDeviceClient, data, "Mobility device client")
        return []
