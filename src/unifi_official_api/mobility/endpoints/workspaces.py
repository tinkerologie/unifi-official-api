"""Workspaces endpoint for UniFi Mobility API."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
        """
        response = await self._client._get("/v1/mobility/workspaces")
        if response is None:
            return []
        data = response.get("data", response) if isinstance(response, dict) else response
        if isinstance(data, list):
            return [WorkspaceSummary.model_validate(item) for item in data]
        return []

    async def get_admins(self, workspace_id: str) -> list[AdminSummary]:
        """
        List administrators of a specific workspace.

        Args:
            workspace_id: Workspace UUID.

        Returns:
            List of AdminSummary objects.
        """
        response = await self._client._get(f"/v1/mobility/workspaces/{workspace_id}/admins")
        if response is None:
            return []
        data = response.get("data", response) if isinstance(response, dict) else response
        if isinstance(data, list):
            return [AdminSummary.model_validate(item) for item in data]
        return []
