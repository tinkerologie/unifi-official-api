"""Sites endpoint for UniFi Site Manager API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...validation import parse_record
from ..models.site import SiteListResponse

if TYPE_CHECKING:
    from ..client import UniFiSiteManagerClient


class SitesEndpoint:
    """Endpoint for listing sites across consoles in UniFi Site Manager."""

    def __init__(self, client: UniFiSiteManagerClient) -> None:
        """
        Initialize the sites endpoint.

        Args:
            client: The UniFi Site Manager client.
        """
        self._client = client

    async def get_all(
        self,
        *,
        limit: int = 25,
        next_token: str | None = None,
    ) -> SiteListResponse:
        """
        List all sites across registered consoles.

        Args:
            limit: Maximum sites to return.
            next_token: Pagination token.

        Returns:
            SiteListResponse containing sites and nextToken.

        Raises:
            UniFiResponseError: If the page in the response fails validation.
        """
        params: dict[str, Any] = {"limit": limit}
        if next_token:
            params["nextToken"] = next_token
        response = await self._client._get("/v1/sites", params=params)
        if isinstance(response, dict):
            return parse_record(SiteListResponse, response, "Site list")
        return SiteListResponse()
