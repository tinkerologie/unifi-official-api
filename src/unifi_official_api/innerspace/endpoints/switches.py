"""Switches endpoint for UniFi InnerSpace API."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any

from unifi_official_api.innerspace.models import InnerSpaceSwitch

if TYPE_CHECKING:
    from unifi_official_api.innerspace.client import UniFiInnerSpaceClient


class SwitchesEndpoint:
    """Endpoint for ``GET /v1/switches``."""

    def __init__(self, client: UniFiInnerSpaceClient) -> None:
        self._client = client

    async def list(
        self,
        site_id: str | None = None,
    ) -> builtins.list[InnerSpaceSwitch]:
        """List switches placed on floor plans in InnerSpace."""
        params: dict[str, Any] = {}
        if site_id is not None:
            params["siteId"] = site_id
        return await self._client._list_collection(
            "/switches",
            ("switches",),
            InnerSpaceSwitch,
            params=params if params else None,
        )

    async def get_all(
        self,
        site_id: str | None = None,
    ) -> builtins.list[InnerSpaceSwitch]:
        """List switches placed on floor plans in InnerSpace."""
        return await self.list(site_id=site_id)


__all__ = ["SwitchesEndpoint"]
