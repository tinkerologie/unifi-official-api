"""Switch stack endpoint for UniFi Network API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...validation import require_record
from ..models.stack import SwitchStack
from .lags import _list_paginated

if TYPE_CHECKING:
    from ..client import UniFiNetworkClient


class StacksEndpoint:
    """
    Endpoint for read-only access to switch stacks.

    Covers UniFi Network 10.4.57 ``/switching/switch-stacks`` resources.
    """

    def __init__(self, client: UniFiNetworkClient) -> None:
        """
        Initialize the stacks endpoint.

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
    ) -> list[SwitchStack]:
        """
        List all switch stacks for a site.

        Automatically paginates through all results when ``offset``/``limit``
        are not explicitly provided.

        Args:
            site_id: The site ID.
            offset: Pagination offset (single-page fetch when set).
            limit: Maximum results (single-page fetch when set).
            filter_str: Optional filter query string.

        Returns:
            List of switch stacks.

        """
        path = self._client.build_api_path(f"/sites/{site_id}/switching/switch-stacks")
        return await _list_paginated(self._client, path, SwitchStack, offset, limit, filter_str)

    async def get(self, site_id: str, switch_stack_id: str) -> SwitchStack:
        """
        Get a specific switch stack.

        Args:
            site_id: The site ID.
            switch_stack_id: The switch stack ID.

        Returns:
            The switch stack.

        Raises:
            UniFiNotFoundError: If the response holds no switch stack.
            UniFiResponseError: If the switch stack in the response fails validation.

        """
        path = self._client.build_api_path(
            f"/sites/{site_id}/switching/switch-stacks/{switch_stack_id}"
        )
        return require_record(
            await self._client._get(path),
            SwitchStack,
            f"Switch stack {switch_stack_id}",
            id_key=None,
        )
