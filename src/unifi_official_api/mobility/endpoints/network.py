"""Network configuration endpoint for UniFi Mobility API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..models.config import UpdateNetworkReq

if TYPE_CHECKING:
    from ..client import UniFiMobilityClient


class NetworkEndpoint:
    """Endpoint for updating LAN / DHCP settings on mobility devices."""

    def __init__(self, client: UniFiMobilityClient) -> None:
        """
        Initialize the network endpoint.

        Args:
            client: The UniFi Mobility client.
        """
        self._client = client

    async def update(
        self,
        workspace_id: str,
        device_id: str,
        config: UpdateNetworkReq | dict[str, Any],
    ) -> None:
        """
        Update LAN / DHCP settings for a device.

        Args:
            workspace_id: Workspace UUID.
            device_id: Device UUID.
            config: Network configuration update payload.
        """
        payload = (
            config.model_dump(by_alias=True, exclude_none=True)
            if isinstance(config, UpdateNetworkReq)
            else config
        )
        await self._client._put(
            f"/v1/mobility/workspaces/{workspace_id}/devices/{device_id}/network",
            json_data=payload,
        )
