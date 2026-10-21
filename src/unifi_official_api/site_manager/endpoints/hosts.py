"""Hosts endpoint for UniFi Site Manager API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..models.host import Host, HostListResponse

if TYPE_CHECKING:
    from ..client import UniFiSiteManagerClient


class HostsEndpoint:
    """Endpoint for managing UniFi hosts via Site Manager."""

    def __init__(self, client: UniFiSiteManagerClient) -> None:
        self._client = client

    async def get_all(
        self,
        *,
        limit: int = 25,
        next_token: str | None = None,
    ) -> HostListResponse:
        params: dict[str, Any] = {"limit": limit}
        if next_token:
            params["nextToken"] = next_token
        response = await self._client._get("/v1/hosts", params=params)
        if isinstance(response, dict):
            return HostListResponse.model_validate(response)
        return HostListResponse()

    async def get(self, host_id: str) -> Host:
        response = await self._client._get(f"/v1/hosts/{host_id}")
        if isinstance(response, dict):
            data = response.get("data", response)
            if isinstance(data, dict) and "id" in data:
                return Host.model_validate(data)
        raise ValueError(f"Host {host_id} not found")
