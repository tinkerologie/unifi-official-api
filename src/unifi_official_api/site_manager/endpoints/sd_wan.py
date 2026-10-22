"""SD-WAN endpoint for UniFi Site Manager API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...validation import parse_records, require_record
from ..models.sd_wan import SDWanConfig, SDWanConfigDetail, SDWanStatus

if TYPE_CHECKING:
    from ..client import UniFiSiteManagerClient


class SDWanEndpoint:
    """Endpoint for managing SD-WAN topologies and monitoring tunnel health."""

    def __init__(self, client: UniFiSiteManagerClient) -> None:
        self._client = client

    async def get_configs(self) -> list[SDWanConfig]:
        response = await self._client._get("/v1/sd-wan-configs")
        if response is None:
            return []
        data = response.get("data", response) if isinstance(response, dict) else response
        if isinstance(data, list):
            return parse_records(SDWanConfig, data, "SD-WAN config")
        return []

    async def get_config(self, config_id: str) -> SDWanConfigDetail:
        response = await self._client._get(f"/v1/sd-wan-configs/{config_id}")
        return require_record(response, SDWanConfigDetail, f"SD-WAN config {config_id}")

    async def get_status(self, config_id: str) -> SDWanStatus:
        response = await self._client._get(f"/v1/sd-wan-configs/{config_id}/status")
        return require_record(response, SDWanStatus, f"SD-WAN status for {config_id}")
