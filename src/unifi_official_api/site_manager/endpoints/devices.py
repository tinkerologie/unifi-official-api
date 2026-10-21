"""Devices endpoint for UniFi Site Manager API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...validation import parse_record
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

        Raises:
            UniFiResponseError: If the page in the response fails validation.
        """
        params: dict[str, Any] = {"limit": limit}
        if next_token:
            params["nextToken"] = next_token
        response = await self._client._get("/v1/devices", params=params)
        if isinstance(response, dict):
            return parse_record(DeviceListResponse, response, "Device list")
        return DeviceListResponse()
