"""Networks endpoint for UniFi Network API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...const import ENDPOINT_NETWORKCONF
from ...validation import created_record, parse_records, require_record, written_record
from ..models import Network

if TYPE_CHECKING:
    from ..client import UniFiNetworkClient


class NetworksEndpoint:
    """Endpoint for managing network configurations."""

    def __init__(self, client: UniFiNetworkClient) -> None:
        """
        Initialize the networks endpoint.

        Args:
            client: The UniFi Network client.

        """
        self._client = client

    async def get_all(
        self,
        site_id: str,
        *,
        offset: int | None = None,
        limit: int | None = None,
        filter_str: str | None = None,
    ) -> list[Network]:
        """
        List all networks.

        Args:
            site_id: The site ID.
            offset: Number of networks to skip (pagination).
            limit: Maximum number of networks to return.
            filter_str: Filter string for network properties.

        Returns:
            List of networks.

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

        path = self._client.build_api_path(f"/sites/{site_id}/networks")
        response = await self._client._get(path, params=params if params else None)

        if response is None:
            return []

        data = response.get("data", response) if isinstance(response, dict) else response
        if isinstance(data, list):
            return parse_records(Network, data, "Network")
        return []

    async def get(self, site_id: str, network_id: str) -> Network:
        """
        Get a specific network.

        Args:
            site_id: The site ID.
            network_id: The network ID.

        Returns:
            The network.

        Raises:
            UniFiNotFoundError: If the response holds no network.
            UniFiResponseError: If the network in the response fails validation.

        """
        path = self._client.build_api_path(f"/sites/{site_id}/networks/{network_id}")
        return require_record(
            await self._client._get(path), Network, f"Network {network_id}", id_key=None
        )

    async def create(
        self,
        site_id: str,
        *,
        name: str,
        vlan_id: int | None = None,
        subnet: str | None = None,
        dhcp_enabled: bool | None = None,
        **kwargs: Any,
    ) -> Network:
        """
        Create a new network.

        Args:
            site_id: The site ID.
            name: Network name.
            vlan_id: VLAN ID.
            subnet: Unsupported legacy argument; use ipv4Configuration instead.
            dhcp_enabled: Unsupported legacy argument; use ipv4Configuration.
            **kwargs: Spec fields. Required: name, vlanId, management and enabled.
                GATEWAY also requires ipv4Configuration, cellularBackupEnabled,
                internetAccessEnabled and isolationEnabled.

        Returns:
            The created network.

        Raises:
            ValueError: If ``subnet`` or ``dhcp_enabled`` is given; no request is made.
            UniFiResponseError: If the console accepted the request but the response
                holds no valid network. The network may have been created.

        """
        path = self._client.build_api_path(f"/sites/{site_id}/networks")
        if subnet is not None or dhcp_enabled is not None:
            msg = (
                "subnet and dhcp_enabled are unsupported; use ipv4Configuration "
                "and management-specific fields: management, enabled, "
                "cellularBackupEnabled, internetAccessEnabled and isolationEnabled"
            )
            raise ValueError(msg)
        data: dict[str, Any] = {"name": name}
        if vlan_id is not None:
            data["vlanId"] = vlan_id
        data.update(kwargs)

        response = await self._client._post(path, json_data=data)
        return created_record(response, Network, "Network", id_key=None)

    async def update(
        self,
        site_id: str,
        network_id: str,
        **kwargs: Any,
    ) -> Network:
        """
        Update a network via full object replacement (PUT).

        The OpenAPI spec requires `name`, `management`, `vlanId`, and
        `enabled`. Keys in kwargs must match the API's camelCase names. Callers
        should read the existing network first and send the complete object.

        Args:
            site_id: The site ID.
            network_id: The network ID.
            **kwargs: Complete network parameters for replacement (camelCase).

        Returns:
            The updated network.

        Raises:
            UniFiNotFoundError: If the follow-up ``get()`` finds no network.
            UniFiResponseError: If the follow-up ``get()`` response fails validation.

        """
        path = self._client.build_api_path(f"/sites/{site_id}/networks/{network_id}")
        written = written_record(
            await self._client._put(path, json_data=kwargs), Network, id_key=None
        )
        if written is not None:
            return written
        return await self.get(site_id, network_id)

    async def delete(self, site_id: str, network_id: str) -> bool:
        """
        Delete a network.

        Args:
            site_id: The site ID.
            network_id: The network ID.

        Returns:
            True if successful.

        """
        path = self._client.build_api_path(f"/sites/{site_id}/networks/{network_id}")
        await self._client._delete(path)
        return True

    async def get_references(self, site_id: str, network_id: str) -> dict[str, Any]:
        """
        Get references to a network.

        Returns information about what resources reference this network,
        such as WiFi broadcasts, firewall rules, or other configurations
        that use this network.

        Args:
            site_id: The site ID.
            network_id: The network ID.

        Returns:
            Dictionary containing references to this network.

        """
        path = self._client.build_api_path(f"/sites/{site_id}/networks/{network_id}/references")
        response = await self._client._get(path)

        if isinstance(response, dict):
            data = response.get("data", response)
            if isinstance(data, dict):
                return data
        return {}

    async def get_legacy_all(self, site_name: str) -> list[dict[str, Any]]:
        """
        List a site's networks from the classic API (``rest/networkconf``).

        Only the fields needed to work out a network's address range are kept,
        so the VPN keys and secrets classic network records can carry never
        leave this method.

        Args:
            site_name: The classic site name (for example ``default``).

        Returns:
            Dicts with ``id``, ``purpose``, ``enabled`` and ``ip_subnet``.

        """
        path = self._client.build_legacy_api_path(site_name, ENDPOINT_NETWORKCONF)
        response = await self._client._get(path)
        data = response.get("data") if isinstance(response, dict) else None
        if not isinstance(data, list):
            return []
        return [
            {
                "id": item.get("_id") or item.get("id"),
                "purpose": item.get("purpose"),
                "enabled": item.get("enabled") is not False,
                "ip_subnet": item.get("ip_subnet"),
            }
            for item in data
            if isinstance(item, dict)
        ]
