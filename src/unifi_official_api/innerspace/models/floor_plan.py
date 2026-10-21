"""Floor plan models for UniFi InnerSpace API."""

from typing import Any

from pydantic import Field

from .project import (
    InnerSpaceBaseModel,
    InnerSpacePlan,
    InnerSpaceProduct,
    InnerSpaceProject,
    InnerSpaceProjectIdentity,
    ProjectData,
    ProjectMeta,
)


class InnerSpaceFloorPlan(InnerSpaceBaseModel):
    """Floor plan metadata returned by ``GET /v1/floor_plans``."""

    id: str = Field(min_length=1)
    name: str = ""
    site_id: str | None = Field(default=None, alias="siteId")
    width: float | None = None
    height: float | None = None
    scale: float | None = None
    image_url: str | None = Field(default=None, alias="imageUrl")
    image_filename: str | None = Field(default=None, alias="imageFilename")
    floor_number: int | None = Field(default=None, alias="floorNumber")
    devices: list[dict[str, Any]] = Field(default_factory=list)


FloorPlan = InnerSpaceFloorPlan

__all__ = [
    "FloorPlan",
    "InnerSpaceFloorPlan",
    "InnerSpacePlan",
    "InnerSpaceProduct",
    "InnerSpaceProject",
    "InnerSpaceProjectIdentity",
    "ProjectData",
    "ProjectMeta",
]
