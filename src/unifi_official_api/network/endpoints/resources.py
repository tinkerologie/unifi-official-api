"""Supporting resources endpoint for UniFi Network API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...validation import parse_records
from ..models.resources import (
    DeviceTag,
    RADIUSProfile,
    VPNServer,
    VPNTunnel,
    WANInterface,
)

if TYPE_CHECKING:
    from ..client import UniFiNetworkClient


class ResourcesEndpoint:
    """Endpoint for accessing supporting network resources."""

    def __init__(self, client: UniFiNetworkClient) -> None:
        """
        Initialize the resources endpoint.

        Args:
            client: The UniFi Network client.

        """
        self._client = client

    # WAN Interfaces

    async def get_wan_interfaces(
        self,
        site_id: str,
        *,
        offset: int | None = None,
        limit: int | None = None,
        filter_str: str | None = None,  # noqa: ARG002 - retained for compatibility
    ) -> list[WANInterface]:
        """
        List all WAN interfaces.

        Args:
            site_id: The site ID.
            offset: Pagination offset.
            limit: Maximum results.
            filter_str: Unsupported by getWansOverviewPage; ignored.

        Returns:
            List of WAN interfaces.

        Raises:
            UniFiResponseError: If an item in the response fails validation.

        """
        params: dict[str, Any] = {}
        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = limit

        path = self._client.build_api_path(f"/sites/{site_id}/wans")
        response = await self._client._get(path, params=params or None)

        if response is None:
            return []

        data = response.get("data", response) if isinstance(response, dict) else response
        if isinstance(data, list):
            return parse_records(WANInterface, data, "WAN interface")
        return []

    # VPN Tunnels

    async def get_vpn_tunnels(
        self,
        site_id: str,
        *,
        offset: int | None = None,
        limit: int | None = None,
        filter_str: str | None = None,
    ) -> list[VPNTunnel]:
        """
        List all site-to-site VPN tunnels.

        Args:
            site_id: The site ID.
            offset: Pagination offset.
            limit: Maximum results.
            filter_str: Filter query string using API filter syntax.

        Returns:
            List of VPN tunnels.

        Raises:
            UniFiResponseError: If an item in the response fails validation.

        """
        params: dict[str, Any] = {}
        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = limit
        if filter_str:
            params["filter"] = filter_str

        path = self._client.build_api_path(f"/sites/{site_id}/vpn/site-to-site-tunnels")
        response = await self._client._get(path, params=params or None)

        if response is None:
            return []

        data = response.get("data", response) if isinstance(response, dict) else response
        if isinstance(data, list):
            return parse_records(VPNTunnel, data, "VPN tunnel")
        return []

    # VPN Servers

    async def get_vpn_servers(
        self,
        site_id: str,
        *,
        offset: int | None = None,
        limit: int | None = None,
        filter_str: str | None = None,
    ) -> list[VPNServer]:
        """
        List all VPN servers.

        Args:
            site_id: The site ID.
            offset: Pagination offset.
            limit: Maximum results.
            filter_str: Filter query string using API filter syntax.

        Returns:
            List of VPN servers.

        Raises:
            UniFiResponseError: If an item in the response fails validation.

        """
        params: dict[str, Any] = {}
        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = limit
        if filter_str:
            params["filter"] = filter_str

        path = self._client.build_api_path(f"/sites/{site_id}/vpn/servers")
        response = await self._client._get(path, params=params if params else None)

        if response is None:
            return []

        data = response.get("data", response) if isinstance(response, dict) else response
        if isinstance(data, list):
            return parse_records(VPNServer, data, "VPN server")
        return []

    # RADIUS Profiles

    async def get_radius_profiles(
        self,
        site_id: str,
        *,
        offset: int | None = None,
        limit: int | None = None,
        filter_str: str | None = None,
    ) -> list[RADIUSProfile]:
        """
        List all RADIUS profiles.

        Args:
            site_id: The site ID.
            offset: Pagination offset.
            limit: Maximum results.
            filter_str: Filter query string using API filter syntax.

        Returns:
            List of RADIUS profiles.

        Raises:
            UniFiResponseError: If an item in the response fails validation.

        """
        params: dict[str, Any] = {}
        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = limit
        if filter_str:
            params["filter"] = filter_str

        path = self._client.build_api_path(f"/sites/{site_id}/radius/profiles")
        response = await self._client._get(path, params=params if params else None)

        if response is None:
            return []

        data = response.get("data", response) if isinstance(response, dict) else response
        if isinstance(data, list):
            return parse_records(RADIUSProfile, data, "RADIUS profile")
        return []

    # Device Tags

    async def get_device_tags(
        self,
        site_id: str,
        *,
        offset: int | None = None,
        limit: int | None = None,
        filter_str: str | None = None,
    ) -> list[DeviceTag]:
        """
        List all device tags.

        Args:
            site_id: The site ID.
            offset: Pagination offset.
            limit: Maximum results.
            filter_str: Filter query string using API filter syntax.

        Returns:
            List of device tags.

        Raises:
            UniFiResponseError: If an item in the response fails validation.

        """
        params: dict[str, Any] = {}
        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = limit
        if filter_str:
            params["filter"] = filter_str

        path = self._client.build_api_path(f"/sites/{site_id}/device-tags")
        response = await self._client._get(path, params=params if params else None)

        if response is None:
            return []

        data = response.get("data", response) if isinstance(response, dict) else response
        if isinstance(data, list):
            return parse_records(DeviceTag, data, "Device tag")
        return []
