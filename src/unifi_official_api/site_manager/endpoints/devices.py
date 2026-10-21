"""Devices endpoint for UniFi Site Manager API."""

from typing import TYPE_CHECKING, Any

from ..models.device import DeviceListResponse

if TYPE_CHECKING:
    from ..client import UniFiSiteManagerClient


class DevicesEndpoint:
    """Endpoint for listing devices across consoles in UniFi Site Manager."""

    def __init__(self, client: UniFiSiteManagerClient) -> None:
        """
        Initialize the devices endpoint.

        Args:
            client: The UniFi Site Manager client.
        """
        self._client = client

    async def get_all(
        self,
        *,
        limit: int = 25,
        next_token: str | None = None,
    ) -> DeviceListResponse:
        """
        List devices grouped by host.

        Args:
            limit: Maximum items to return.
            next_token: Pagination token.

        Returns:
            DeviceListResponse with host device groups.
        """
        params: dict[str, Any] = {"limit": limit}
        if next_token:
            params["nextToken"] = next_token
        response = await self._client._get("/v1/devices", params=params)
        if isinstance(response, dict):
            return DeviceListResponse.model_validate(response)
        return DeviceListResponse()
