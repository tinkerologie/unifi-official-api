"""Device endpoints for the UniFi Access developer API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import AccessDevice, parse_records

if TYPE_CHECKING:
    from ..client import UniFiAccessClient


class DevicesEndpoint:
    """
    List Access devices (hubs, readers and intercoms).

    Verified against the Ubiquiti UniFi Access API Reference V2.2.10 (Section 8.1).
    """

    def __init__(self, client: UniFiAccessClient) -> None:
        """Initialize the endpoint group."""
        self._client = client

    async def get_all(self) -> list[AccessDevice]:
        """Return every Access device (``view:device``)."""
        response = await self._client._get("devices")
        return parse_records(response, AccessDevice, "devices")
