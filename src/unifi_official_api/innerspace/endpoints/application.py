"""Application endpoint for UniFi InnerSpace API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from unifi_official_api.innerspace.models.application import ApplicationInfo
from unifi_official_api.validation import require_record

if TYPE_CHECKING:
    from unifi_official_api.innerspace.client import UniFiInnerSpaceClient


class ApplicationEndpoint:
    """Endpoint for InnerSpace application metadata."""

    def __init__(self, client: UniFiInnerSpaceClient) -> None:
        self._client = client

    async def get_info(self) -> ApplicationInfo:
        """Retrieve InnerSpace application information."""
        response = await self._client._get(self._client.build_api_path("/info"))
        return require_record(response, ApplicationInfo, "InnerSpace application info", id_key=None)


__all__ = ["ApplicationEndpoint"]
