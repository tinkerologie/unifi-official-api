"""Project models for UniFi InnerSpace API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class InnerSpaceBaseModel(BaseModel):
    """Base model for UniFi InnerSpace API payloads."""

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class InnerSpaceProjectIdentity(InnerSpaceBaseModel):
    """Identity block inside an InnerSpace project response."""

    id: str = Field(min_length=1)
    name: str | None = None
    title: str | None = None
    version: str | None = None


class InnerSpacePlan(InnerSpaceBaseModel):
    """Floor plan (2D/3D space) inside an InnerSpace project."""

    id: str = Field(min_length=1)
    name: str | None = None
    site_id: str | None = Field(default=None, alias="siteId")
    scale: float | None = None
    image_filename: str | None = Field(default=None, alias="imageFilename")
    width: int | None = None
    height: int | None = None


class InnerSpaceProduct(InnerSpaceBaseModel):
    """Placed UniFi product inside an InnerSpace project."""

    id: str = Field(min_length=1)
    name: str | None = None
    model: str | None = None
    mac: str | None = None
    plan_id: str | None = Field(default=None, alias="planId")


class InnerSpaceProject(InnerSpaceBaseModel):
    """Top-level response for ``GET /v1/project``."""

    project: InnerSpaceProjectIdentity | None = None
    plans: list[InnerSpacePlan] = Field(default_factory=list)
    products: list[InnerSpaceProduct] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _populate_root_project(cls, data: Any) -> Any:
        """Populate project identity when root-level project fields are returned."""
        if isinstance(data, dict) and "project" not in data:
            root_keys = ("id", "title", "name", "model", "environment")
            if any(k in data for k in root_keys):
                copied = dict(data)
                copied["project"] = {k: data[k] for k in root_keys if k in data}
                return copied
        return data


ProjectMeta = InnerSpaceProjectIdentity
ProjectData = InnerSpaceProject

__all__ = [
    "InnerSpaceBaseModel",
    "InnerSpacePlan",
    "InnerSpaceProduct",
    "InnerSpaceProject",
    "InnerSpaceProjectIdentity",
    "ProjectData",
    "ProjectMeta",
]
