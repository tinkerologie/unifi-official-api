"""Site models for UniFi Site Manager."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SiteMeta(BaseModel):
    """Site metadata."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    name: str | None = None
    desc: str | None = None
    timezone: str | None = None


class SiteStatistics(BaseModel):
    """Site summary statistics."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    device_count: int | None = Field(default=None, alias="deviceCount")
    client_count: int | None = Field(default=None, alias="clientCount")


class SiteManagerSite(BaseModel):
    """Site entry in UniFi Site Manager."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    site_id: str = Field(alias="siteId")
    host_id: str = Field(alias="hostId")
    meta: SiteMeta | None = None
    statistics: SiteStatistics | None = None
    permission: str | None = None
    is_owner: bool | None = Field(default=None, alias="isOwner")


class SiteListResponse(BaseModel):
    """Response envelope for listing sites."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    data: list[SiteManagerSite] = Field(default_factory=list)
    next_token: str | None = Field(default=None, alias="nextToken")
