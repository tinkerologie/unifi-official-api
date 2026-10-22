"""VPN Clients endpoint for UniFi Network API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from ...const import (
    ENDPOINT_NETWORKCONF,
    ENDPOINT_VPN_CONNECTIONS,
)
from ...exceptions import UniFiNotFoundError, UniFiResponseError
from ...validation import parse_record, sanitized_validation_fields, written_record
from ..models.vpn_client import VpnClient

if TYPE_CHECKING:
    from ..client import UniFiNetworkClient

_LOGGER = logging.getLogger(__name__)


class VpnClientsEndpoint:
    """
    Endpoint for managing VPN Client network configurations.

    Targets the controller endpoint:
    ``/proxy/network/api/s/{site_name}/rest/networkconf``
    """

    def __init__(self, client: UniFiNetworkClient) -> None:
        """Initialize the VPN Clients endpoint."""
        self._client = client

    def _extract_items(self, response: Any) -> list[dict[str, Any]]:
        """Extract data items from a legacy response envelope."""
        if response is None:
            return []

        if isinstance(response, dict):
            meta = response.get("meta")
            if isinstance(meta, dict) and meta.get("rc") == "error":
                msg = meta.get("msg", "UniFi Network API error")
                raise UniFiResponseError(msg, status_code=200, response_body=str(response))

            data = response.get("data", response)
            if isinstance(data, list):
                return [item for item in data if isinstance(item, dict)]
            if isinstance(data, dict):
                return [data]
            return []

        if isinstance(response, list):
            return [item for item in response if isinstance(item, dict)]

        return []

    async def list_site_to_site_vpns(self, site_name: str = "default") -> list[dict[str, Any]]:
        """
        List the site-to-site VPN tunnels configured for a site.

        These are the ``rest/networkconf`` entries with purpose ``site-vpn``
        (IPsec, OpenVPN and SD-WAN hub-and-spoke tunnels alike). Only the
        fields entities need are returned, so no keys or peer secrets are
        carried into coordinator data.

        Args:
            site_name: The UniFi classic site name (default: "default").

        Returns:
            Dicts with ``id``, ``name``, ``vpn_type`` and ``enabled``.

        """
        path = self._client.build_legacy_api_path(site_name, ENDPOINT_NETWORKCONF)
        items = self._extract_items(await self._client._get(path))
        return [
            {
                "id": tunnel_id,
                "name": item.get("name"),
                "vpn_type": item.get("vpn_type"),
                "enabled": item.get("enabled") is not False,
            }
            for item in items
            if item.get("purpose") == "site-vpn"
            and isinstance(tunnel_id := item.get("_id") or item.get("id"), str)
        ]

    async def list_vpn_connections(self, site_name: str = "default") -> list[dict[str, Any]]:
        """
        List the live connection state of VPN clients and site-to-site tunnels.

        Targets ``/proxy/network/v2/api/site/{site_name}/vpn/connections``,
        which reports one entry per connected (or connecting) VPN, keyed by
        the ``network_id`` of its ``rest/networkconf`` entry. Addresses and
        traffic rates are dropped: only identity, type and status are kept.

        Args:
            site_name: The UniFi classic site name (default: "default").

        Returns:
            Dicts with ``network_id``, ``type`` and ``status``.

        Raises:
            UniFiResponseError: If the response has no ``connections`` list.

        """
        path = self._client.build_legacy_v2_api_path(site_name, ENDPOINT_VPN_CONNECTIONS)
        response = await self._client._get(path)
        connections = response.get("connections") if isinstance(response, dict) else None
        if not isinstance(connections, list):
            # An unreadable payload must not read as "no VPN connected",
            # which would report every tunnel as disconnected.
            msg = "Unexpected VPN connections response"
            raise UniFiResponseError(msg, status_code=200)
        return [
            {
                "network_id": connection["network_id"],
                "type": connection.get("type"),
                "status": connection.get("status"),
            }
            for connection in connections
            if isinstance(connection, dict) and isinstance(connection.get("network_id"), str)
        ]

    async def list_vpn_clients(self, site_name: str = "default") -> list[VpnClient]:
        """
        List all VPN Client connections configured for a site.

        Args:
            site_name: The UniFi classic site name (default: "default").

        Returns:
            List of VpnClient models.

        """
        path = self._client.build_legacy_api_path(site_name, ENDPOINT_NETWORKCONF)
        response = await self._client._get(path)
        items = self._extract_items(response)

        clients: list[VpnClient] = []
        for item in items:
            if item.get("purpose") != "vpn-client":
                continue
            try:
                clients.append(VpnClient.model_validate(item))
            except ValidationError as err:
                _LOGGER.debug(
                    "Skipping invalid VPN client item (%s: %s)",
                    type(err).__name__,
                    sanitized_validation_fields(err),
                )
                continue

        return clients

    async def get_vpn_client(self, site_name: str, client_id: str) -> VpnClient:
        """
        Get a specific VPN client configuration by ID.

        Args:
            site_name: The UniFi classic site name.
            client_id: The ID of the VPN client network.

        Returns:
            The VpnClient model.

        Raises:
            UniFiNotFoundError: If neither the client read nor the client listing holds
                the VPN client.
            UniFiResponseError: If the VPN client found fails validation.

        """
        record = await self._find_vpn_client_record(site_name, client_id)
        if record is None:
            msg = f"VPN Client {client_id} not found"
            raise UniFiNotFoundError(msg, status_code=200)
        return parse_record(VpnClient, record, f"VPN Client {client_id}")

    @staticmethod
    def _match_vpn_client(items: list[dict[str, Any]], client_id: str) -> dict[str, Any] | None:
        """Return the VPN client record with this ID, or None."""
        for item in items:
            if (item.get("_id") == client_id or item.get("id") == client_id) and item.get(
                "purpose"
            ) == "vpn-client":
                return item
        return None

    async def _find_vpn_client_record(
        self, site_name: str, client_id: str
    ) -> dict[str, Any] | None:
        """
        Return the raw record of a VPN client, or None.

        The client read is tried first, then the raw listing. The listing is
        searched raw, not through ``list_vpn_clients()``, which skips a record
        that fails validation: that client exists and must not read as missing.
        """
        path = self._client.build_legacy_api_path(site_name, f"{ENDPOINT_NETWORKCONF}/{client_id}")
        record = self._match_vpn_client(
            self._extract_items(await self._client._get(path)), client_id
        )
        if record is None:
            list_path = self._client.build_legacy_api_path(site_name, ENDPOINT_NETWORKCONF)
            list_items = self._extract_items(await self._client._get(list_path))
            record = self._match_vpn_client(list_items, client_id)
        return record

    async def update_vpn_client(
        self,
        site_name: str,
        client_id: str,
        *,
        enabled: bool | None = None,
        **kwargs: Any,
    ) -> VpnClient:
        """
        Update a VPN client configuration (e.g. enable/disable).

        Args:
            site_name: The UniFi classic site name.
            client_id: The ID of the VPN client network.
            enabled: Set enabled state (True/False).
            **kwargs: Additional fields to update.

        Returns:
            The updated VpnClient model.

        Raises:
            UniFiNotFoundError: If neither the client read nor the client listing holds
                the VPN client, or the follow-up ``get_vpn_client()`` after a ``PUT``
                acknowledged without a valid client finds none.
            UniFiResponseError: If the follow-up ``get_vpn_client()`` finds a client
                that fails validation.

        """
        path = self._client.build_legacy_api_path(site_name, f"{ENDPOINT_NETWORKCONF}/{client_id}")
        current_payload = await self._find_vpn_client_record(site_name, client_id)
        if current_payload is None:
            msg = f"VPN Client {client_id} not found"
            raise UniFiNotFoundError(msg, status_code=200)

        current_payload = dict(current_payload)
        if enabled is not None:
            current_payload["enabled"] = enabled

        current_payload.update(kwargs)

        put_response = await self._client._put(path, json_data=current_payload)
        echo = self._match_vpn_client(self._extract_items(put_response), client_id)
        if echo is not None:
            written = written_record(echo, VpnClient, id_key=None)
            if written is not None:
                return written
        return await self.get_vpn_client(site_name, client_id)
