"""Workspace and Admin models for UniFi Mobility."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AdminPermission(BaseModel):
    """Admin mobility permission."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    umr: str | None = None


class AdminSummary(BaseModel):
    """Workspace administrator summary."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    name: str
    email: str
    status: str = "ACTIVE"
    is_owner: bool = Field(alias="is_owner")
    permissions: AdminPermission | dict[str, Any] | None = None


class WorkspaceSummary(BaseModel):
    """UniFi Mobility workspace."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    workspace_id: str = Field(alias="workspace_id")
    workspace_name: str = Field(alias="workspace_name")
    is_owner: bool = Field(alias="is_owner")
    status: str = "ACTIVE"
