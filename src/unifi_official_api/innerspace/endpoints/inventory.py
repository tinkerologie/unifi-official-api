"""Inventory endpoint for UniFi InnerSpace API."""

import builtins
from typing import TYPE_CHECKING, Any

from unifi_official_api.innerspace.models import InnerSpaceInventoryDevice

if TYPE_CHECKING:
    from unifi_official_api.innerspace.client import UniFiInnerSpaceClient


class InventoryEndpoint:
    """Endpoint for ``GET /v1/inventory``."""

    def __init__(self, client: UniFiInnerSpaceClient) -> None:
        self._client = client

    async def list(
        self,
        site_id: str | None = None,
    ) -> builtins.list[InnerSpaceInventoryDevice]:
        """List all devices known to InnerSpace (placed and unplaced)."""
        params: dict[str, Any] = {}
        if site_id is not None:
            params["siteId"] = site_id
        return await self._client._list_collection(
            "/inventory",
            ("inventory", "devices"),
            InnerSpaceInventoryDevice,
            params=params if params else None,
        )

    async def get_all(
        self,
        site_id: str | None = None,
    ) -> builtins.list[InnerSpaceInventoryDevice]:
        """List all devices known to InnerSpace (alias for ``list``)."""
        return await self.list(site_id=site_id)

    async def get_inventory(
        self,
        site_id: str | None = None,
    ) -> builtins.list[InnerSpaceInventoryDevice]:
        """List all devices known to InnerSpace (alias for ``list``)."""
        return await self.list(site_id=site_id)


__all__ = ["InventoryEndpoint"]
