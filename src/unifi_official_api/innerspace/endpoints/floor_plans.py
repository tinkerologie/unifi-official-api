"""Floor plans endpoint for UniFi InnerSpace API."""

import builtins
from typing import TYPE_CHECKING, Any

from unifi_official_api.innerspace.models import InnerSpaceFloorPlan, InnerSpaceProject

from .assets import _validate_asset_segment

if TYPE_CHECKING:
    from unifi_official_api.innerspace.client import UniFiInnerSpaceClient


class FloorPlansEndpoint:
    """Endpoint for ``GET /v1/floor_plans`` and floor plan operations."""

    def __init__(self, client: UniFiInnerSpaceClient) -> None:
        self._client = client

    @staticmethod
    def _validate_asset_segment(segment: str, name: str = "segment") -> str:
        """Validate and URL-quote an InnerSpace asset path segment."""
        return _validate_asset_segment(segment, name)

    async def get_project(
        self,
        mode: str | None = None,
        *,
        expected_unsupported: bool = False,
    ) -> InnerSpaceProject:
        """Fetch the InnerSpace project, plans, and placed products."""
        return await self._client.project.get(
            mode=mode,
            expected_unsupported=expected_unsupported,
        )

    async def list(
        self,
        site_id: str | None = None,
    ) -> builtins.list[InnerSpaceFloorPlan]:
        """List floor plans configured in InnerSpace."""
        params: dict[str, Any] = {}
        if site_id is not None:
            params["siteId"] = site_id
        return await self._client._list_collection(
            "/floor_plans",
            ("floor_plans", "floorPlans", "plans"),
            InnerSpaceFloorPlan,
            params=params if params else None,
        )

    async def get_all(
        self,
        site_id: str | None = None,
    ) -> builtins.list[InnerSpaceFloorPlan]:
        """List floor plans configured in InnerSpace (alias for ``list``)."""
        return await self.list(site_id=site_id)

    async def get_image(self, plan_id: str, filename: str) -> bytes:
        """Download raw floor plan asset image bytes."""
        return (await self.download_image(plan_id, filename))[0]

    async def download_image(
        self,
        plan_id: str,
        filename: str,
    ) -> tuple[bytes, str]:
        """Download a floor plan asset image and return ``(bytes, content_type)``."""
        return await self._client.assets.download_floor_plan_image(plan_id, filename)


__all__ = ["FloorPlansEndpoint"]
