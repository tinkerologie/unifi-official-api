"""Wireless configuration endpoint for UniFi Mobility API."""

from typing import TYPE_CHECKING, Any

from ..models.config import UpdateWirelessReq

if TYPE_CHECKING:
    from ..client import UniFiMobilityClient


class WirelessEndpoint:
    """Endpoint for updating WiFi SSID and password on mobility devices."""

    def __init__(self, client: UniFiMobilityClient) -> None:
        """
        Initialize the wireless endpoint.

        Args:
            client: The UniFi Mobility client.
        """
        self._client = client

    async def update(
        self,
        workspace_id: str,
        device_id: str,
        config: UpdateWirelessReq | dict[str, Any],
    ) -> None:
        """
        Update wireless SSID and password for a device.

        Args:
            workspace_id: Workspace UUID.
            device_id: Device UUID.
            config: Wireless configuration payload (ssid and password).
        """
        payload = (
            config.model_dump(by_alias=True, exclude_none=True)
            if isinstance(config, UpdateWirelessReq)
            else config
        )
        await self._client._put(
            f"/v1/mobility/workspaces/{workspace_id}/devices/{device_id}/wireless",
            json_data=payload,
        )
