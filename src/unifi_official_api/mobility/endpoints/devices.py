"""Devices endpoint for UniFi Mobility API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...validation import parse_records, require_record
from ..models.config import UpdateDeviceNameReq
from ..models.device import MobilityDeviceDetail, MobilityDeviceSummary

if TYPE_CHECKING:
    from ..client import UniFiMobilityClient


class DevicesEndpoint:
    """Endpoint for managing mobility router devices."""

    def __init__(self, client: UniFiMobilityClient) -> None:
        self._client = client

    async def get_all(self, workspace_id: str) -> list[MobilityDeviceSummary]:
        response = await self._client._get(f"/v1/mobility/workspaces/{workspace_id}/devices")
        if response is None:
            return []
        data = response.get("data", response) if isinstance(response, dict) else response
        if isinstance(data, list):
            return parse_records(MobilityDeviceSummary, data, "Mobility device")
        return []

    async def get(self, workspace_id: str, device_id: str) -> MobilityDeviceDetail:
        response = await self._client._get(
            f"/v1/mobility/workspaces/{workspace_id}/devices/{device_id}"
        )
        return require_record(
            response, MobilityDeviceDetail, f"Device {device_id} in workspace {workspace_id}"
        )

    async def update_name(
        self,
        workspace_id: str,
        device_id: str,
        name: str | UpdateDeviceNameReq,
    ) -> None:
        payload = {"name": name} if isinstance(name, str) else name.model_dump(by_alias=True)
        await self._client._put(
            f"/v1/mobility/workspaces/{workspace_id}/devices/{device_id}", json_data=payload
        )
