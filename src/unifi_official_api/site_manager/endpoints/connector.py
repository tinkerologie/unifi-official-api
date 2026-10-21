"""Cloud Connector proxy endpoint for UniFi Site Manager API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..client import UniFiSiteManagerClient


class ConnectorEndpoint:
    """
    Endpoint for proxying arbitrary HTTP requests to consoles via Site Manager Cloud Connector.
    """

    def __init__(self, client: UniFiSiteManagerClient) -> None:
        """
        Initialize the Cloud Connector endpoint.

        Args:
            client: The UniFi Site Manager client.
        """
        self._client = client

    async def proxy(
        self,
        console_id: str,
        path: str,
        *,
        method: str = "GET",
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any] | None:
        """
        Proxy an API request to an on-premises UniFi console.

        Args:
            console_id: The target console hardware ID.
            path: The relative path on the console (e.g. "network/integration/v1/sites").
            method: HTTP method.
            json_data: Optional JSON body.
            params: Optional query params.

        Returns:
            Parsed JSON response from the proxied console.
        """
        clean_path = path.lstrip("/")
        full_path = f"/v1/connector/consoles/{console_id}/{clean_path}"
        return await self._client._request(
            method=method.upper(),
            path=full_path,
            json_data=json_data,
            params=params,
        )
