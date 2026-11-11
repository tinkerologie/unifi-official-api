"""UniFi Site Manager API client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, NoReturn

from ..auth import ApiKeyAuth
from ..base import BaseUniFiClient
from ..const import (
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_TIMEOUT,
    SITE_MANAGER_API_BASE_URL,
)
from ..exceptions import UniFiError, UniFiResponseError
from .endpoints import (
    ConnectorEndpoint,
    DevicesEndpoint,
    HostsEndpoint,
    ISPMetricsEndpoint,
    SDWanEndpoint,
    SitesEndpoint,
)

if TYPE_CHECKING:
    from datetime import datetime

    import aiohttp

_MAX_PAGES = 100
_MAX_ITEMS = 10_000


class UniFiSiteManagerClient(BaseUniFiClient):
    """
    Async client for the UniFi Site Manager API (api.ui.com).

    Provides cloud-level management of consoles/hosts, sites, device inventories,
    ISP metric telemetry, SD-WAN topologies, and Cloud Connector proxying.
    """

    _HOSTS_PATH = "/v1/hosts"

    def _response_log_text(self, response_text: str, *, limit: int) -> str:
        """Keep account-wide inventory and metadata out of transport logs."""
        return "[Site Manager response omitted]"[:limit] if response_text else "empty"

    def __init__(
        self,
        auth: ApiKeyAuth,
        *,
        base_url: str = SITE_MANAGER_API_BASE_URL,
        session: aiohttp.ClientSession | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        connect_timeout: int = DEFAULT_CONNECT_TIMEOUT,
    ) -> None:
        """Initialize the UniFi Site Manager client."""
        super().__init__(
            auth=auth,
            base_url=base_url,
            session=session,
            timeout=timeout,
            connect_timeout=connect_timeout,
        )

        # Initialize endpoints
        self._hosts = HostsEndpoint(self)
        self._sites = SitesEndpoint(self)
        self._devices = DevicesEndpoint(self)
        self._isp_metrics = ISPMetricsEndpoint(self)
        self._sd_wan = SDWanEndpoint(self)
        self._connector = ConnectorEndpoint(self)

    @property
    def hosts(self) -> HostsEndpoint:
        """Access hosts management endpoints."""
        return self._hosts

    @property
    def sites(self) -> SitesEndpoint:
        """Access multi-site management endpoints."""
        return self._sites

    @property
    def devices(self) -> DevicesEndpoint:
        """Access cross-console device inventory endpoints."""
        return self._devices

    @property
    def isp_metrics(self) -> ISPMetricsEndpoint:
        """Access ISP WAN telemetry metrics endpoints."""
        return self._isp_metrics

    @property
    def sd_wan(self) -> SDWanEndpoint:
        """Access SD-WAN configuration and status endpoints."""
        return self._sd_wan

    @property
    def sdwan(self) -> SDWanEndpoint:
        """Alias for sd_wan endpoint."""
        return self._sd_wan

    @property
    def connector(self) -> ConnectorEndpoint:
        """Access Site Manager Cloud Connector proxy endpoint."""
        return self._connector

    async def validate_connection(self) -> bool:
        """Validate credentials by querying accessible hosts."""
        try:
            response = await self._get(self._HOSTS_PATH, params={"limit": 1})
            return response is not None
        except UniFiError, ValueError:
            return False

    async def list_hosts(self) -> list[dict[str, Any]]:
        """Return host dictionaries from all pages."""
        return await self._list_paginated(self._HOSTS_PATH)

    async def get_host(self, host_id: str) -> dict[str, Any]:
        """Return detailed information for a specific host."""
        path = self._host_path(host_id)
        data = await self._get(path)
        return self._extract_object(data, path)

    async def list_sites(self) -> list[dict[str, Any]]:
        """Return all accessible UniFi sites."""
        return await self._list_paginated("/v1/sites")

    async def list_devices(self, host_ids: list[str] | None = None) -> list[dict[str, Any]]:
        """Return devices grouped by host, merged across every result page."""
        params: dict[str, Any] | None = None
        if host_ids:
            params = {"hostIds[]": host_ids}

        pages = await self._list_paginated("/v1/devices", params=params)
        groups: dict[str, dict[str, Any]] = {}
        anonymous_groups: list[dict[str, Any]] = []

        for group in pages:
            devices = group.get("devices")
            if devices is None:
                devices = []
            if not isinstance(devices, list) or not all(
                isinstance(device, dict) for device in devices
            ):
                self._raise_response_error("/v1/devices returned malformed devices")
            host_id = group.get("hostId")
            if not isinstance(host_id, str) or not host_id:
                anonymous_groups.append({**group, "devices": devices})
                continue

            existing = groups.get(host_id)
            if existing is None:
                groups[host_id] = {**group, "devices": list(devices)}
                continue

            existing.update({key: value for key, value in group.items() if key != "devices"})
            existing_devices = existing["devices"]
            existing_devices.extend(devices)

        return [*groups.values(), *anonymous_groups]

    async def get_isp_metrics(
        self,
        begin_timestamp: datetime | None = None,
        end_timestamp: datetime | None = None,
        *,
        metric_type: Literal["5m", "1h"] = "5m",
        duration: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return host and site records for an interval without pagination.

        The API accepts ``24h`` with ``5m``, or ``7d`` or ``30d`` with ``1h``.
        Use either a duration or timezone-aware timestamps.
        """
        path = self._isp_metrics_path(metric_type)
        params = self._isp_metrics_params(begin_timestamp, end_timestamp, duration)
        data = await self._get(path, params=params)
        return self._extract_data(data, path)

    async def query_isp_metrics(
        self,
        metric_type: Literal["5m", "1h"],
        sites: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Query ISP metrics for specified sites and time ranges without pagination."""
        path = self._isp_metrics_query_path(metric_type)
        data = await self._post(path, json_data=self._isp_metrics_query_body(sites))
        return self._extract_object(data, path)

    async def list_sd_wan_configs(self) -> list[dict[str, Any]]:
        """Return all SD-WAN configurations."""
        data = await self._get("/v1/sd-wan-configs")
        return self._extract_data(data, "/v1/sd-wan-configs")

    async def get_sd_wan_config(self, config_id: str) -> dict[str, Any]:
        """Return detailed information for a specific SD-WAN configuration."""
        path = f"/v1/sd-wan-configs/{config_id}"
        data = await self._get(path)
        return self._extract_object(data, path)

    async def get_sd_wan_config_status(self, config_id: str) -> dict[str, Any]:
        """Return deployment and connection status for an SD-WAN config."""
        path = f"/v1/sd-wan-configs/{config_id}/status"
        data = await self._get(path)
        return self._extract_object(data, path)

    def _host_path(self, host_id: str) -> str:
        """Return the path for a single Site Manager host."""
        return f"{self._HOSTS_PATH}/{host_id}"

    @staticmethod
    def _page_params(
        *, page_size: int | None = None, next_token: str | None = None
    ) -> dict[str, int | str]:
        """Build query parameters for a Site Manager page."""
        params: dict[str, int | str] = {}
        if page_size is not None:
            params["pageSize"] = page_size
        if next_token:
            params["nextToken"] = next_token
        return params

    async def _get_list_page(
        self, path: str, params: dict[str, Any]
    ) -> dict[str, Any] | list[Any] | None:
        """Fetch a page and retain the response envelope."""
        return await self._get(path, params=params or None)

    async def _list_paginated(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Return all pages from a Site Manager list endpoint."""
        items: list[dict[str, Any]] = []
        next_token: str | None = None
        seen_tokens: set[str] = set()

        for _ in range(_MAX_PAGES):
            page_params = dict(params or {}) | self._page_params(next_token=next_token)
            response = await self._get_list_page(path, page_params)
            page = self._extract_data(response, path)
            if len(items) + len(page) > _MAX_ITEMS:
                self._raise_response_error(f"{path} exceeded the item limit")
            items.extend(page)

            token = self._extract_next_token(response, path)
            if token is None:
                return items
            if not page:
                self._raise_response_error(f"{path} returned an empty page with nextToken")
            if token in seen_tokens:
                self._raise_response_error(f"{path} repeated nextToken")
            seen_tokens.add(token)
            next_token = token

        msg = f"{path} exceeded the page limit"
        raise UniFiResponseError(msg, status_code=200)

    @staticmethod
    def _isp_metrics_path(interval: str) -> str:
        return f"/v1/isp-metrics/{interval}"

    def _isp_metrics_query_path(self, interval: str) -> str:
        return f"{self._isp_metrics_path(interval)}/query"

    def _isp_metrics_params(
        self,
        begin_timestamp: datetime | None = None,
        end_timestamp: datetime | None = None,
        duration: str | None = None,
        *,
        host_id: str | None = None,
    ) -> dict[str, str] | None:
        """Build ISP metrics query parameters and format timestamps."""
        params = self._isp_metrics_timestamps(begin_timestamp, end_timestamp)
        if host_id:
            params["hostId"] = host_id
        if duration is not None:
            params["duration"] = duration
        return params or None

    def _isp_metrics_timestamps(
        self, begin_timestamp: datetime | None, end_timestamp: datetime | None
    ) -> dict[str, str]:
        return {
            name: self._format_timestamp(timestamp)
            for name, timestamp in (
                ("beginTimestamp", begin_timestamp),
                ("endTimestamp", end_timestamp),
            )
            if timestamp is not None
        }

    @staticmethod
    def _isp_metrics_query_body(sites: list[dict[str, Any]]) -> dict[str, Any]:
        return {"sites": sites}

    @staticmethod
    def _format_timestamp(timestamp: datetime) -> str:
        """Format an aware datetime as an RFC3339 timestamp."""
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            msg = "Timestamps must include a UTC offset"
            raise ValueError(msg)

        return timestamp.isoformat().replace("+00:00", "Z")

    def _extract_data(
        self,
        response: dict[str, Any] | list[Any] | None,
        path: str,
    ) -> list[dict[str, Any]]:
        """Validate and return a Site Manager response envelope's data list."""
        if not isinstance(response, dict):
            self._raise_response_error(f"{path} returned a malformed response envelope")

        data = self._response_data(response)
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            self._raise_response_error(f"{path} returned malformed data")

        return data

    def _extract_object(
        self,
        response: dict[str, Any] | list[Any] | None,
        path: str,
    ) -> dict[str, Any]:
        """Validate and return a Site Manager response envelope's data object."""
        if not isinstance(response, dict):
            self._raise_response_error(f"{path} returned a malformed response envelope")

        data = self._response_data(response)
        if not isinstance(data, dict):
            self._raise_response_error(f"{path} returned malformed data")

        return data

    @staticmethod
    def _response_data(response: object, *, fallback: object = None) -> object:
        """Select the data value or return the adapter's fallback."""
        if isinstance(response, dict):
            return response.get("data", fallback)
        return fallback

    def _extract_next_token(
        self,
        response: dict[str, Any] | list[Any] | None,
        path: str,
    ) -> str | None:
        """Validate and return an optional pagination token."""
        if not isinstance(response, dict):
            self._raise_response_error(f"{path} returned a malformed response envelope")

        token = response.get("nextToken")
        if token is None:
            return None
        if not isinstance(token, str) or not token:
            self._raise_response_error(f"{path} returned an invalid nextToken")
        return token

    @staticmethod
    def _raise_response_error(message: str) -> NoReturn:
        """Raise a response error for a successful but malformed payload."""
        raise UniFiResponseError(message, status_code=200)


__all__ = ["UniFiSiteManagerClient"]
