"""Traffic Matching endpoint for UniFi Network API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..models.traffic import (
    Country,
    DPIApplication,
    DPICategory,
    TrafficMatchingList,
    TrafficMatchingType,
)

if TYPE_CHECKING:
    from ..client import UniFiNetworkClient


_MAX_PORT_NUMBER = 65535


class TrafficEndpoint:
    """Endpoint for managing traffic matching lists and DPI resources."""

    def __init__(self, client: UniFiNetworkClient) -> None:
        """
        Initialize the traffic endpoint.

        Args:
            client: The UniFi Network client.

        """
        self._client = client

    # Traffic Matching Lists

    async def get_all_lists(
        self,
        site_id: str,
        *,
        offset: int | None = None,
        limit: int | None = None,
        filter_str: str | None = None,
    ) -> list[TrafficMatchingList]:
        """
        List all traffic matching lists.

        Args:
            site_id: The site ID.
            offset: Pagination offset.
            limit: Maximum results (max 200).
            filter_str: Filter query string using API filter syntax.
                Example: "type.eq('IP_ADDRESS')" or "name.like('block*')"

        Returns:
            List of traffic matching lists.

        """
        params: dict[str, Any] = {}
        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = min(limit, 200)
        if filter_str:
            params["filter"] = filter_str

        path = self._client.build_api_path(f"/sites/{site_id}/traffic-matching-lists")
        response = await self._client._get(path, params=params or None)

        if response is None:
            return []

        data = response.get("data", response) if isinstance(response, dict) else response
        if isinstance(data, list):
            return [TrafficMatchingList.model_validate(item) for item in data]
        return []

    async def get_list(self, site_id: str, list_id: str) -> TrafficMatchingList:
        """
        Get a specific traffic matching list.

        Args:
            site_id: The site ID.
            list_id: The list ID.

        Returns:
            The traffic matching list.

        """
        path = self._client.build_api_path(f"/sites/{site_id}/traffic-matching-lists/{list_id}")
        response = await self._client._get(path)

        if isinstance(response, dict):
            data = response.get("data", response)
            if isinstance(data, dict):
                return TrafficMatchingList.model_validate(data)
            if isinstance(data, list) and len(data) > 0:
                return TrafficMatchingList.model_validate(data[0])
        raise ValueError(f"Traffic matching list {list_id} not found")

    async def create_list(
        self,
        site_id: str,
        *,
        name: str,
        list_type: TrafficMatchingType,
        entries: list[str] | None = None,
        items: list[dict[str, Any]] | None = None,
        description: str | None = None,
    ) -> TrafficMatchingList:
        """
        Create a new traffic matching list.

        Args:
            site_id: The site ID.
            name: List name.
            list_type: List type.
            entries: Single integer port strings for PORTS lists only (1-65535).
            items: Pre-built spec items, mutually exclusive with entries.
            description: Unsupported legacy argument; the schema has no description.

        Returns:
            The created traffic matching list.

        """
        path = self._client.build_api_path(f"/sites/{site_id}/traffic-matching-lists")
        if description is not None:
            msg = "description is unsupported for traffic matching lists"
            raise ValueError(msg)
        if entries is not None and items is not None:
            msg = "Supply either entries or items, not both"
            raise ValueError(msg)
        if entries is not None:
            if list_type != TrafficMatchingType.PORTS:
                msg = "Use items for non-PORTS traffic matching lists"
                raise ValueError(msg)
            items = []
            for entry in entries:
                if not entry.isascii() or not entry.isdecimal():
                    msg = "Use items for port ranges or non-integer entries"
                    raise ValueError(msg)
                port = int(entry)
                if not 1 <= port <= _MAX_PORT_NUMBER:
                    msg = "Use items with port numbers in the range 1-65535"
                    raise ValueError(msg)
                items.append({"type": "PORT_NUMBER", "value": port})
        if not items:
            msg = "items must contain at least one item"
            raise ValueError(msg)
        data: dict[str, Any] = {
            "name": name,
            "type": list_type.value,
            "items": items,
        }

        response = await self._client._post(path, json_data=data)

        if isinstance(response, dict):
            result = response.get("data", response)
            if isinstance(result, dict):
                return TrafficMatchingList.model_validate(result)
        raise ValueError("Failed to create traffic matching list")

    async def update_list(
        self,
        site_id: str,
        list_id: str,
        **kwargs: Any,
    ) -> TrafficMatchingList:
        """
        Update a traffic matching list.

        Args:
            site_id: The site ID.
            list_id: The list ID.
            **kwargs: Parameters to update.

        Returns:
            The updated traffic matching list.

        """
        path = self._client.build_api_path(f"/sites/{site_id}/traffic-matching-lists/{list_id}")
        response = await self._client._put(path, json_data=kwargs)

        if isinstance(response, dict):
            result = response.get("data", response)
            if isinstance(result, dict):
                return TrafficMatchingList.model_validate(result)
        raise ValueError("Failed to update traffic matching list")

    async def delete_list(self, site_id: str, list_id: str) -> bool:
        """
        Delete a traffic matching list.

        Args:
            site_id: The site ID.
            list_id: The list ID.

        Returns:
            True if successful.

        """
        path = self._client.build_api_path(f"/sites/{site_id}/traffic-matching-lists/{list_id}")
        await self._client._delete(path)
        return True

    # DPI Resources

    async def get_dpi_categories(
        self,
        *,
        offset: int | None = None,
        limit: int | None = None,
        filter_str: str | None = None,
    ) -> list[DPICategory]:
        """
        List all DPI categories.

        Args:
            offset: Pagination offset.
            limit: Maximum results (max 200).
            filter_str: Filter query string using API filter syntax.

        Returns:
            List of DPI categories.

        """
        params: dict[str, Any] = {}
        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = min(limit, 200)
        if filter_str:
            params["filter"] = filter_str

        path = self._client.build_api_path("/dpi/categories")
        response = await self._client._get(path, params=params or None)

        if response is None:
            return []

        data = response.get("data", response) if isinstance(response, dict) else response
        if isinstance(data, list):
            return [DPICategory.model_validate(item) for item in data]
        return []

    async def get_dpi_applications(
        self,
        *,
        offset: int | None = None,
        limit: int | None = None,
        filter_str: str | None = None,
    ) -> list[DPIApplication]:
        """
        List all DPI applications.

        Args:
            offset: Pagination offset.
            limit: Maximum results (max 200).
            filter_str: Filter query string using API filter syntax.

        Returns:
            List of DPI applications.

        """
        params: dict[str, Any] = {}
        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = min(limit, 200)
        if filter_str:
            params["filter"] = filter_str

        path = self._client.build_api_path("/dpi/applications")
        response = await self._client._get(path, params=params or None)

        if response is None:
            return []

        data = response.get("data", response) if isinstance(response, dict) else response
        if isinstance(data, list):
            return [DPIApplication.model_validate(item) for item in data]
        return []

    async def get_countries(
        self,
        *,
        offset: int | None = None,
        limit: int | None = None,
        filter_str: str | None = None,
    ) -> list[Country]:
        """
        List all countries/regions.

        Args:
            offset: Pagination offset.
            limit: Maximum results (max 200).
            filter_str: Filter query string using API filter syntax.

        Returns:
            List of countries.

        """
        params: dict[str, Any] = {}
        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = min(limit, 200)
        if filter_str:
            params["filter"] = filter_str

        path = self._client.build_api_path("/countries")
        response = await self._client._get(path, params=params or None)

        if response is None:
            return []

        data = response.get("data", response) if isinstance(response, dict) else response
        if isinstance(data, list):
            return [Country.model_validate(item) for item in data]
        return []
