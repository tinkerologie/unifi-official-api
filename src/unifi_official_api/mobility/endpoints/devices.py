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

    async def get_all(
        self, workspace_id: str, *, limit: int | None = None, offset: int | None = None
    ) -> list[MobilityDeviceSummary]:
        """Return one page of device summaries. Set ``offset`` to read a later page."""
        path = self._client._devices_path(workspace_id)
        response = await self._client._get_list_page(path, limit=limit, offset=offset)
        data = self._client._list_data(response, allow_bare_list=True)
        return parse_records(MobilityDeviceSummary, data or [], "Mobility device")

    async def get(self, workspace_id: str, device_id: str) -> MobilityDeviceDetail:
        """Return the detail record of one device."""
        response = await self._client._get(self._client._device_path(workspace_id, device_id))
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
