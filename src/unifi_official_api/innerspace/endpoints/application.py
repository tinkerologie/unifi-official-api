"""Application endpoint for UniFi InnerSpace API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from unifi_official_api.innerspace.models.application import ApplicationInfo

if TYPE_CHECKING:
    from unifi_official_api.innerspace.client import UniFiInnerSpaceClient


class ApplicationEndpoint:
    """Endpoint for InnerSpace application metadata."""

    def __init__(self, client: UniFiInnerSpaceClient) -> None:
        self._client = client

    async def get_info(self) -> ApplicationInfo:
        """Retrieve InnerSpace application information."""
        response = await self._client._get(self._client.build_api_path("/info"))
        if isinstance(response, dict):
            data = response.get("data", response)
            if isinstance(data, dict):
                return ApplicationInfo.model_validate(data)
        msg = "Unable to retrieve InnerSpace application info"
        raise ValueError(msg)


__all__ = ["ApplicationEndpoint"]
