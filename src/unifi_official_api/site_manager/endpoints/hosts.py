"""Hosts endpoint for UniFi Site Manager API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...validation import parse_record, require_record
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
            return parse_record(HostListResponse, response, "Host list")
        return HostListResponse()

    async def get(self, host_id: str) -> Host:
        response = await self._client._get(f"/v1/hosts/{host_id}")
        return require_record(response, Host, f"Host {host_id}")
