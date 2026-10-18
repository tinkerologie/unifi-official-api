"""UniFi InnerSpace API client."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, TypeVar, cast

import aiohttp
from pydantic import BaseModel, ValidationError

from unifi_official_api.auth import LocalAuth
from unifi_official_api.base import BaseUniFiClient
from unifi_official_api.const import (
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_TIMEOUT,
    INNERSPACE_API_BASE_URL,
    INNERSPACE_INTEGRATION_PATH,
    ConnectionType,
)
from unifi_official_api.exceptions import (
    UniFiConnectionError,
    UniFiResponseError,
    UniFiTimeoutError,
)
from unifi_official_api.innerspace.endpoints import (
    MAX_ASSET_SEGMENT_LENGTH,
    AccessPointsEndpoint,
    ApplicationEndpoint,
    AssetsEndpoint,
    FloorPlansEndpoint,
    InventoryEndpoint,
    ProjectEndpoint,
    SwitchesEndpoint,
    is_valid_asset_segment,
)
from unifi_official_api.innerspace.models import (
    ApplicationInfo,
    InnerSpaceAccessPoint,
    InnerSpaceFloorPlan,
    InnerSpaceInventoryDevice,
    InnerSpaceProject,
    InnerSpaceSwitch,
)

if TYPE_CHECKING:
    import aiohttp

    from unifi_official_api.auth import ApiKeyAuth

_LOGGER = logging.getLogger(__name__)

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class UniFiInnerSpaceClient(BaseUniFiClient):
    """Async client for the UniFi InnerSpace Integration API (v1.0.4)."""

    def __init__(
        self,
        auth: ApiKeyAuth | LocalAuth,
        *,
        base_url: str | None = None,
        connection_type: ConnectionType = ConnectionType.LOCAL,
        console_id: str | None = None,
        session: aiohttp.ClientSession | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        connect_timeout: int = DEFAULT_CONNECT_TIMEOUT,
    ) -> None:
        """Initialize the UniFi InnerSpace client."""
        if connection_type == ConnectionType.LOCAL:
            if not base_url:
                raise ValueError("base_url is required for LOCAL connection type")
            effective_base_url = base_url
        else:
            if not console_id:
                raise ValueError("console_id is required for REMOTE connection type")
            effective_base_url = base_url or INNERSPACE_API_BASE_URL

        super().__init__(
            auth=auth,
            base_url=effective_base_url,
            session=session,
            timeout=timeout,
            connect_timeout=connect_timeout,
        )
        self._connection_type = connection_type
        self._console_id = console_id

        self.project = ProjectEndpoint(self)
        self.floor_plans = FloorPlansEndpoint(self)
        self.access_points = AccessPointsEndpoint(self)
        self.switches = SwitchesEndpoint(self)
        self.inventory = InventoryEndpoint(self)
        self.assets = AssetsEndpoint(self)
        self.application = ApplicationEndpoint(self)

    @property
    def connection_type(self) -> ConnectionType:
        """Return the connection type."""
        return self._connection_type

    @property
    def console_id(self) -> str | None:
        """Return the console ID (for remote connections)."""
        return self._console_id

    def _ssl_for_request(self) -> bool | None:
        """Return the SSL verify flag for the request."""
        if isinstance(self._auth, LocalAuth):
            return self._auth.verify_ssl
        return None

    def build_api_path(self, endpoint: str) -> str:
        """Build the full API path for an InnerSpace endpoint."""
        endpoint = endpoint.lstrip("/")
        if self._connection_type == ConnectionType.LOCAL:
            return f"{INNERSPACE_INTEGRATION_PATH}/{endpoint}"
        connector_path = INNERSPACE_INTEGRATION_PATH.removeprefix("/proxy")
        return f"/v1/connector/consoles/{self._console_id}{connector_path}/{endpoint}"

    def _build_api_path(self, endpoint: str) -> str:
        """Build the full API path for an InnerSpace endpoint."""
        return self.build_api_path(endpoint)

    @staticmethod
    def _unwrap_object(response: Any, *, endpoint: str) -> dict[str, Any]:
        """Unwrap a top-level dict or ``{"data": {...}}`` envelope."""
        if isinstance(response, dict):
            nested = response.get("data")
            if isinstance(nested, dict):
                return nested
            return response
        raise UniFiResponseError(
            f"Unexpected InnerSpace {endpoint} response type: {type(response).__name__}",
            status_code=200,
        )

    @staticmethod
    def _raise_malformed(endpoint: str) -> None:
        """Raise a UniFiResponseError for malformed responses."""
        ep = endpoint if endpoint.startswith("/v1/") else f"/v1/{endpoint.lstrip('/')}"
        msg = f"{ep} returned a malformed response"
        raise UniFiResponseError(msg, status_code=200)

    @classmethod
    def _extract_list(
        cls,
        response: Any,
        keys: tuple[str, ...] | str,
        *,
        endpoint: str,
    ) -> list[dict[str, Any]]:
        """Extract a list of dicts from an InnerSpace response."""
        if response is None:
            return []
        key_list = (keys,) if isinstance(keys, str) else keys
        raw_items: Any = None
        if isinstance(response, list):
            raw_items = response
        elif isinstance(response, dict):
            raw = None
            for key in key_list:
                raw = response.get(key)
                if raw is not None:
                    break
            if raw is None and "data" in response:
                data = response.get("data")
                if isinstance(data, list):
                    raw = data
                elif isinstance(data, dict):
                    for key in key_list:
                        raw = data.get(key)
                        if raw is not None:
                            break
            if raw is None:
                cls._raise_malformed(endpoint)
            raw_items = raw
        else:
            cls._raise_malformed(endpoint)

        if not isinstance(raw_items, list) or not all(isinstance(item, dict) for item in raw_items):
            cls._raise_malformed(endpoint)

        return cast(list[dict[str, Any]], raw_items)

    async def _list_collection(
        self,
        endpoint: str,
        keys: tuple[str, ...],
        model_cls: type[_ModelT],
        *,
        params: dict[str, Any] | None = None,
    ) -> list[_ModelT]:
        """Fetch and validate a list collection from an InnerSpace endpoint."""
        response = await self._get(self.build_api_path(endpoint), params=params)
        raw_items = self._extract_list(response, keys, endpoint=endpoint)
        results: list[_ModelT] = []
        for idx, item in enumerate(raw_items):
            try:
                results.append(model_cls.model_validate(item))
            except ValidationError as err:
                _LOGGER.warning(
                    "Skipping malformed %s item at index %d (id=%r) in %s: %s",
                    model_cls.__name__,
                    idx,
                    item.get("id"),
                    endpoint,
                    err,
                )
        return results

    async def get_project(
        self,
        mode: str | None = None,
        *,
        expected_unsupported: bool = False,
    ) -> InnerSpaceProject:
        """Fetch the InnerSpace project, plans, and placed products."""
        return await self.project.get(
            mode=mode,
            expected_unsupported=expected_unsupported,
        )

    async def list_floor_plans(
        self,
        site_id: str | None = None,
    ) -> list[InnerSpaceFloorPlan]:
        """List floor plans configured in InnerSpace."""
        return await self.floor_plans.list(site_id=site_id)

    async def list_access_points(
        self,
        site_id: str | None = None,
    ) -> list[InnerSpaceAccessPoint]:
        """List access points placed on floor plans in InnerSpace."""
        return await self.access_points.list(site_id=site_id)

    async def list_switches(
        self,
        site_id: str | None = None,
    ) -> list[InnerSpaceSwitch]:
        """List switches placed on floor plans in InnerSpace."""
        return await self.switches.list(site_id=site_id)

    async def list_inventory(
        self,
        site_id: str | None = None,
    ) -> list[InnerSpaceInventoryDevice]:
        """List all devices known to InnerSpace (placed and unplaced)."""
        return await self.inventory.list(site_id=site_id)

    async def get_inventory(
        self,
        site_id: str | None = None,
    ) -> list[InnerSpaceInventoryDevice]:
        """List all devices known to InnerSpace (placed and unplaced)."""
        return await self.inventory.list(site_id=site_id)

    async def download_floor_plan_image(
        self,
        plan_id: str,
        filename: str,
    ) -> tuple[bytes, str]:
        """Download a floor plan asset image and return ``(bytes, content_type)``."""
        return await self.assets.download_floor_plan_image(plan_id, filename)

    async def get_application_info(self) -> ApplicationInfo:
        """Retrieve InnerSpace application information."""
        return await self.application.get_info()

    async def validate_connection(self) -> bool:
        """Return True if the InnerSpace API is reachable and valid."""
        try:
            await self.get_project()
        except Exception:
            return False
        else:
            return True

    async def get_binary(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> bytes:
        """Download binary data from an endpoint path."""
        session = await self._ensure_session()
        url = self._build_url(path)
        headers = self._get_headers()
        headers.pop("Content-Type", None)
        headers["Accept"] = "*/*"

        try:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status >= 400:
                    raise UniFiConnectionError(
                        f"Failed to fetch binary asset: HTTP {response.status}"
                    )
                return await response.read()
        except TimeoutError as err:
            raise UniFiTimeoutError(f"Request to {url} timed out") from err
        except aiohttp.ClientError as err:
            raise UniFiConnectionError(f"Request to {url} failed: {err}") from err


__all__ = [
    "MAX_ASSET_SEGMENT_LENGTH",
    "UniFiInnerSpaceClient",
    "is_valid_asset_segment",
]
