"""Access points endpoint for UniFi InnerSpace API."""

import builtins
from typing import TYPE_CHECKING, Any

from unifi_official_api.innerspace.models import InnerSpaceAccessPoint

if TYPE_CHECKING:
    from unifi_official_api.innerspace.client import UniFiInnerSpaceClient


class AccessPointsEndpoint:
    """Endpoint for ``GET /v1/access_points``."""

    def __init__(self, client: UniFiInnerSpaceClient) -> None:
        self._client = client

    async def list(
        self,
        site_id: str | None = None,
    ) -> builtins.list[InnerSpaceAccessPoint]:
        """List access points placed on floor plans in InnerSpace."""
        params: dict[str, Any] = {}
        if site_id is not None:
            params["siteId"] = site_id
        return await self._client._list_collection(
            "/access_points",
            ("access_points", "accessPoints"),
            InnerSpaceAccessPoint,
            params=params if params else None,
        )

    async def get_all(
        self,
        site_id: str | None = None,
    ) -> builtins.list[InnerSpaceAccessPoint]:
        """List access points placed on floor plans in InnerSpace."""
        return await self.list(site_id=site_id)


__all__ = ["AccessPointsEndpoint"]
