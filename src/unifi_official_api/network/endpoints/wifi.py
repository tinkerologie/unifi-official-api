"""WiFi endpoint for UniFi Network API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...exceptions import UniFiNotFoundError
from ...validation import (
    created_record,
    parse_records,
    require_record,
    response_record,
    written_record,
)
from ..models import WifiNetwork, WifiSecurity

if TYPE_CHECKING:
    from ..client import UniFiNetworkClient


_STANDARD_BROADCAST_DEFAULTS: dict[str, Any] = {
    "type": "STANDARD",
    "enabled": True,
    "channel2gLockedTo6": False,
    "clientIsolationEnabled": False,
    "dtimPeriod2gLockedTo3": False,
    "multicastToUnicastConversionEnabled": False,
    "uapsdEnabled": False,
    "advertiseDeviceName": False,
    "arpProxyEnabled": False,
    "broadcastingFrequenciesGHz": [2.4, 5],
    "bssTransitionEnabled": False,
}


class WifiEndpoint:
    """Endpoint for managing WiFi configurations."""

    @staticmethod
    def _extract_wifi_payload(
        response: dict[str, Any] | list[Any] | None,
    ) -> dict[str, Any] | None:
        """Extract a WiFi broadcast payload from API responses."""
        record = response_record(response, id_key=None)
        return dict(record) if record is not None else None

    def __init__(self, client: UniFiNetworkClient) -> None:
        """
        Initialize the WiFi endpoint.

        Args:
            client: The UniFi Network client.

        """
        self._client = client

    async def get_legacy_configs(self, site_name: str) -> list[dict[str, Any]]:
        """
        List WLAN configurations from the classic API.

        The official Integration API redacts secrets (``ssid``, ``passphrase``,
        ``security`` are returned as ``null``). The classic ``/rest/wlanconf``
        endpoint exposes the SSID name, passphrase, and security mode, which are
        required to build WiFi QR codes.

        Args:
            site_name: The classic site name (for example ``default``).

        Returns:
            List of raw WLAN configuration dictionaries.

        """
        path = self._client.build_legacy_api_path(site_name, "/rest/wlanconf")
        response = await self._client._get(path, log_body=False)

        if response is None:
            return []

        data = response.get("data", response) if isinstance(response, dict) else response
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []

    async def get_all(
        self,
        site_id: str,
        *,
        offset: int | None = None,
        limit: int | None = None,
        filter_str: str | None = None,
    ) -> list[WifiNetwork]:
        """
        List all WiFi networks.

        Args:
            site_id: The site ID.
            offset: Number of WiFi networks to skip (pagination).
            limit: Maximum number of WiFi networks to return.
            filter_str: Filter string for WiFi properties.

        Returns:
            List of WiFi networks.

        Raises:
            UniFiResponseError: If an item in the response fails validation.

        """
        params: dict[str, Any] = {}
        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = limit
        if filter_str:
            params["filter"] = filter_str

        path = self._client.build_api_path(f"/sites/{site_id}/wifi/broadcasts")
        response = await self._client._get(path, params=params if params else None)

        if response is None:
            return []

        data = response.get("data", response) if isinstance(response, dict) else response
        if isinstance(data, list):
            return parse_records(WifiNetwork, data, "WiFi network")
        return []

    async def get(self, site_id: str, wifi_id: str) -> WifiNetwork:
        """
        Get a specific WiFi network.

        Args:
            site_id: The site ID.
            wifi_id: The WiFi network ID.

        Returns:
            The WiFi network.

        Raises:
            UniFiNotFoundError: If the response holds no WiFi network.
            UniFiResponseError: If the WiFi network in the response fails validation.

        """
        path = self._client.build_api_path(f"/sites/{site_id}/wifi/broadcasts/{wifi_id}")
        response = await self._client._get(path)
        return require_record(response, WifiNetwork, f"WiFi network {wifi_id}", id_key=None)

    async def create(
        self,
        site_id: str,
        *,
        name: str,
        ssid: str,
        passphrase: str | None = None,
        security: WifiSecurity = WifiSecurity.WPA2,
        network_id: str | None = None,
        hidden: bool = False,
        **kwargs: Any,
    ) -> WifiNetwork:
        """
        Create a new WiFi network.

        Args:
            site_id: The site ID.
            name: Broadcast name and SSID.
            ssid: Must match name; the API has a single broadcast name.
            passphrase: WiFi password (required for WPA2, rejected for OPEN).
            security: OPEN or WPA2; other types require securityConfiguration.
            network_id: Associated network ID.
            hidden: Whether to hide the SSID.
            **kwargs: Additional parameters.

        Returns:
            The created WiFi network.

        Raises:
            ValueError: If ``ssid`` differs from ``name`` or the security settings are
                invalid; no request is made.
            UniFiResponseError: If the console accepted the request but the response
                holds no valid WiFi network. The network may have been created.

        """
        path = self._client.build_api_path(f"/sites/{site_id}/wifi/broadcasts")
        if ssid != name:
            msg = "ssid must match name; the API has one broadcast name"
            raise ValueError(msg)
        security_configuration: dict[str, Any]
        if "securityConfiguration" in kwargs:
            security_configuration = kwargs["securityConfiguration"]
        elif security in (WifiSecurity.OPEN, WifiSecurity.OPEN_UPPER):
            if passphrase is not None:
                msg = "OPEN security does not accept a passphrase"
                raise ValueError(msg)
            security_configuration = {"type": "OPEN"}
        elif security in (WifiSecurity.WPA2, WifiSecurity.WPA2_PERSONAL):
            if not passphrase:
                msg = "WPA2 requires a passphrase"
                raise ValueError(msg)
            security_configuration = {
                "type": "WPA2_PERSONAL",
                "passphrase": passphrase,
            }
        else:
            msg = "Use securityConfiguration for unsupported security types"
            raise ValueError(msg)
        data: dict[str, Any] = {
            **_STANDARD_BROADCAST_DEFAULTS,
            "broadcastingFrequenciesGHz": list(
                _STANDARD_BROADCAST_DEFAULTS["broadcastingFrequenciesGHz"]
            ),
            "name": name,
            "hideName": hidden,
            "securityConfiguration": security_configuration,
        }
        if network_id is not None:
            data["network"] = {"type": "SPECIFIC", "networkId": network_id}
        data.update(kwargs)

        response = await self._client._post(path, json_data=data)
        return created_record(response, WifiNetwork, "WiFi network", id_key=None)

    async def update(
        self,
        site_id: str,
        wifi_id: str,
        **kwargs: Any,
    ) -> WifiNetwork:
        """
        Update a WiFi network.

        Args:
            site_id: The site ID.
            wifi_id: The WiFi network ID.
            **kwargs: Parameters to update.

        Returns:
            The updated WiFi network.

        Raises:
            UniFiNotFoundError: If the current WiFi network read, or the follow-up
                ``get()`` after a ``PUT`` acknowledged without a valid network,
                holds no network.
            UniFiResponseError: If the follow-up ``get()`` response fails validation.

        """
        path = self._client.build_api_path(f"/sites/{site_id}/wifi/broadcasts/{wifi_id}")
        current_payload = self._extract_wifi_payload(await self._client._get(path))
        if current_payload is None:
            msg = f"WiFi network {wifi_id} not found"
            raise UniFiNotFoundError(msg, status_code=200)

        # UniFi Network expects a full WiFi broadcast document via PUT rather than
        # a partial PATCH payload for updates on current controller versions.
        current_payload.pop("id", None)
        current_payload.pop("metadata", None)
        current_payload.update(kwargs)

        response = await self._client._put(path, json_data=current_payload)
        written = written_record(response, WifiNetwork, id_key=None)
        if written is not None:
            return written
        return await self.get(site_id, wifi_id)

    async def delete(self, site_id: str, wifi_id: str) -> bool:
        """
        Delete a WiFi network.

        Args:
            site_id: The site ID.
            wifi_id: The WiFi network ID.

        Returns:
            True if successful.

        """
        path = self._client.build_api_path(f"/sites/{site_id}/wifi/broadcasts/{wifi_id}")
        await self._client._delete(path)
        return True
