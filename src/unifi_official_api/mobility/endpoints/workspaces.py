"""Workspaces endpoint for UniFi Mobility API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...validation import parse_records
from ..models.workspace import AdminSummary, WorkspaceSummary

if TYPE_CHECKING:
    from ..client import UniFiMobilityClient


class WorkspacesEndpoint:
    """Endpoint for managing UniFi Mobility workspaces and admins."""

    def __init__(self, client: UniFiMobilityClient) -> None:
        """
        Initialize the workspaces endpoint.

        Args:
            client: The UniFi Mobility client.
        """
        self._client = client

    async def get_all(self) -> list[WorkspaceSummary]:
        """
        List all mobility workspaces visible to the authenticated user.

        Returns:
            List of WorkspaceSummary objects.

        Raises:
            UniFiResponseError: If an item in the response fails validation.
        """
        response = await self._client._get_list_page(self._client._WORKSPACES_PATH)
        data = self._client._list_data(response, allow_bare_list=True)
        return parse_records(WorkspaceSummary, data or [], "Mobility workspace")

    async def get_admins(self, workspace_id: str) -> list[AdminSummary]:
        """
        List administrators of a specific workspace.

        Args:
            workspace_id: Workspace UUID.

        Returns:
            List of AdminSummary objects.

        Raises:
            UniFiResponseError: If an item in the response fails validation.
        """
        path = self._client._workspace_admins_path(workspace_id)
        response = await self._client._get_list_page(path)
        data = self._client._list_data(response, allow_bare_list=True)
        return parse_records(AdminSummary, data or [], "Mobility workspace admin")
