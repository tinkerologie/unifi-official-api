"""Hosts endpoint for UniFi Site Manager API."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
        """Return one host page. Pass its ``next_token`` to read the next page."""
        params = self._client._page_params(page_size=limit, next_token=next_token)
        response = await self._client._get_list_page(self._client._HOSTS_PATH, params)
        if isinstance(response, dict):
            return parse_record(HostListResponse, response, "Host list")
        return HostListResponse()

    async def get(self, host_id: str) -> Host:
        """Return one host by its ID."""
        response = await self._client._get(self._client._host_path(host_id))
        return require_record(response, Host, f"Host {host_id}")
