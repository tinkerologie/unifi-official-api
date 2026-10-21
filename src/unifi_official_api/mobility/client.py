"""UniFi Mobility API client."""

import re
from typing import TYPE_CHECKING, Any, ClassVar, Literal, NoReturn, TypeIs

from ..auth import ApiKeyAuth
from ..base import BaseUniFiClient
from ..const import (
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_TIMEOUT,
    MOBILITY_API_BASE_URL,
    MOBILITY_RATE_LIMIT_REQUESTS,
    MOBILITY_RATE_LIMIT_WINDOW,
)
from ..exceptions import (
    UniFiResponseError,
    UniFiValidationError,
)
from .endpoints import (
    ClientsEndpoint,
    DevicesEndpoint,
    NetworkEndpoint,
    WirelessEndpoint,
    WorkspacesEndpoint,
)

if TYPE_CHECKING:
    import aiohttp

_WORKSPACES_PATH = "/v1/mobility/workspaces"
_PAGE_SIZE = 200
_MAX_ITEMS = 5_000
_MAX_PAGES = _MAX_ITEMS // _PAGE_SIZE
_ID_PATTERN = re.compile(r"[0-9A-Za-z-]{1,64}")


def is_valid_mobility_id(identifier: Any) -> TypeIs[str]:
    """Return True if a workspace or device id is a plain path segment."""
    return isinstance(identifier, str) and bool(_ID_PATTERN.fullmatch(identifier))


class UniFiMobilityClient(BaseUniFiClient):
    """
    Async client for the UniFi Mobility API (api.ui.com).

    Provides cloud management of mobility router gateways (UMR devices),
    workspaces, connected clients, and remote network/wireless configurations.
    """

    RATE_LIMIT: ClassVar[tuple[int, float] | None] = (
        MOBILITY_RATE_LIMIT_REQUESTS,
        MOBILITY_RATE_LIMIT_WINDOW,
    )

    def _response_log_text(self, response_text: str, *, limit: int) -> str:
        """Keep router inventory, IP addresses and GPS fixes out of logs."""
        return "[Mobility response omitted]"[:limit] if response_text else "empty"

    def __init__(
        self,
        auth: ApiKeyAuth,
        *,
        base_url: str = MOBILITY_API_BASE_URL,
        session: aiohttp.ClientSession | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        connect_timeout: int = DEFAULT_CONNECT_TIMEOUT,
    ) -> None:
        """Initialize the UniFi Mobility client."""
        super().__init__(
            auth=auth,
            base_url=base_url,
            session=session,
            timeout=timeout,
            connect_timeout=connect_timeout,
        )

        # Initialize endpoints
        self._workspaces = WorkspacesEndpoint(self)
        self._devices = DevicesEndpoint(self)
        self._clients = ClientsEndpoint(self)
        self._network = NetworkEndpoint(self)
        self._wireless = WirelessEndpoint(self)

    @property
    def workspaces(self) -> WorkspacesEndpoint:
        """Access workspace and admin management endpoints."""
        return self._workspaces

    @property
    def devices(self) -> DevicesEndpoint:
        """Access mobility router device management endpoints."""
        return self._devices

    @property
    def clients(self) -> ClientsEndpoint:
        """Access connected client monitoring endpoints."""
        return self._clients

    @property
    def network(self) -> NetworkEndpoint:
        """Access LAN/DHCP configuration endpoints."""
        return self._network

    @property
    def wireless(self) -> WirelessEndpoint:
        """Access WiFi configuration endpoints."""
        return self._wireless

    async def validate_connection(self) -> bool:
        """Validate authentication with api.ui.com."""
        await self.list_workspaces()
        return True

    async def list_workspaces(self) -> list[dict[str, Any]]:
        """Return every Mobility workspace the API key can access."""
        response = await self._get(_WORKSPACES_PATH)
        return self._extract_list(response, _WORKSPACES_PATH)

    async def list_workspace_admins(self, workspace_id: str) -> list[dict[str, Any]]:
        """Return every admin for a workspace with their permission levels."""
        path = f"{_WORKSPACES_PATH}/{self._safe_id(workspace_id)}/admins"
        response = await self._get(path)
        return self._extract_list(response, path)

    async def _list_paginated(self, path: str) -> list[dict[str, Any]]:
        """Paginate a Mobility collection up to the item and page limits."""
        items: list[dict[str, Any]] = []

        for _ in range(_MAX_PAGES):
            response = await self._get(path, params={"limit": _PAGE_SIZE, "offset": len(items)})
            page = self._extract_list(response, path)
            if len(items) + len(page) > _MAX_ITEMS:
                self._raise_response_error(f"{path} exceeded the item limit")
            items.extend(page)

            total = response.get("total") if isinstance(response, dict) else None
            reached_total = (
                isinstance(total, int) and not isinstance(total, bool) and len(items) >= total
            )
            if reached_total or len(page) < _PAGE_SIZE:
                return items

        return self._raise_response_error(f"{path} exceeded the page limit")

    async def list_devices(self, workspace_id: str) -> list[dict[str, Any]]:
        """Return the summary of every device in a workspace."""
        path = f"{_WORKSPACES_PATH}/{self._safe_id(workspace_id)}/devices"
        return await self._list_paginated(path)

    async def list_device_clients(self, workspace_id: str, device_id: str) -> list[dict[str, Any]]:
        """Return every client associated with a device."""
        path = (
            f"{_WORKSPACES_PATH}/{self._safe_id(workspace_id)}"
            f"/devices/{self._safe_id(device_id)}/clients"
        )
        return await self._list_paginated(path)

    async def get_device(self, workspace_id: str, device_id: str) -> dict[str, Any]:
        """Return the detail record of one device."""
        path = (
            f"{_WORKSPACES_PATH}/{self._safe_id(workspace_id)}/devices/{self._safe_id(device_id)}"
        )
        response = await self._get(path)
        if not isinstance(response, dict) or not isinstance(data := response.get("data"), dict):
            self._raise_response_error(f"{path} returned a malformed device")
        return data

    async def update_device_name(
        self,
        workspace_id: str,
        device_id: str,
        *,
        name: str,
    ) -> None:
        """Update the user-assigned display name of a device."""
        if not isinstance(name, str):
            msg = "Device name is required"
            raise UniFiValidationError(msg)

        path = (
            f"{_WORKSPACES_PATH}/{self._safe_id(workspace_id)}/devices/{self._safe_id(device_id)}"
        )
        await self._put(path, json_data={"name": name})

    async def update_device_network(
        self,
        workspace_id: str,
        device_id: str,
        *,
        host_address: str | None = None,
        dhcp_mode: Literal["dhcp", "none"] | None = None,
        dhcp_range_start: str | None = None,
        dhcp_range_stop: str | None = None,
        dhcp_lease_time: int | None = None,
    ) -> None:
        """Update LAN / DHCP settings for a device."""
        body: dict[str, Any] = {}
        if host_address is not None:
            body["host_address"] = host_address
        if dhcp_mode is not None:
            body["dhcp_mode"] = dhcp_mode
        if dhcp_range_start is not None:
            body["dhcp_range_start"] = dhcp_range_start
        if dhcp_range_stop is not None:
            body["dhcp_range_stop"] = dhcp_range_stop
        if dhcp_lease_time is not None:
            body["dhcp_lease_time"] = dhcp_lease_time

        path = (
            f"{_WORKSPACES_PATH}/{self._safe_id(workspace_id)}"
            f"/devices/{self._safe_id(device_id)}/network"
        )
        await self._put(path, json_data=body)

    async def update_device_wireless(
        self,
        workspace_id: str,
        device_id: str,
        *,
        ssid: str,
        password: str,
    ) -> None:
        """Update WiFi SSID and password for a device."""
        if not isinstance(ssid, str) or not isinstance(password, str):
            msg = "Both ssid and password are required"
            raise UniFiValidationError(msg)

        path = (
            f"{_WORKSPACES_PATH}/{self._safe_id(workspace_id)}"
            f"/devices/{self._safe_id(device_id)}/wireless"
        )
        await self._put(path, json_data={"ssid": ssid, "password": password})

    @staticmethod
    def _safe_id(identifier: Any) -> str:
        """Return an id that is safe to use as a URL path segment."""
        if not is_valid_mobility_id(identifier):
            msg = "Invalid Mobility identifier"
            raise UniFiValidationError(msg)
        return identifier

    def _extract_list(
        self,
        response: dict[str, Any] | list[Any] | None,
        path: str,
    ) -> list[dict[str, Any]]:
        """Validate and return a Mobility envelope's list of records."""
        if not isinstance(response, dict):
            self._raise_response_error(f"{path} returned a malformed response envelope")

        data = response.get("data")
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            self._raise_response_error(f"{path} returned malformed data")

        return data

    @staticmethod
    def _raise_response_error(message: str) -> NoReturn:
        """Raise a response error for a successful but malformed payload."""
        raise UniFiResponseError(message, status_code=200)


__all__ = [
    "UniFiMobilityClient",
    "is_valid_mobility_id",
]
