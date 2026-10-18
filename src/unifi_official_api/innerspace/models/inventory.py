"""Inventory models for UniFi InnerSpace API."""

from __future__ import annotations

from pydantic import Field

from .project import InnerSpaceBaseModel


class InnerSpaceInventoryDevice(InnerSpaceBaseModel):
    """Device inventory entry returned by ``GET /v1/inventory``."""

    id: str = Field(min_length=1)
    name: str = ""
    mac: str | None = None
    model: str | None = None
    type: str | None = None
    placed: bool = False
    floor_plan_id: str | None = Field(default=None, alias="floorPlanId")
    x: float | None = None
    y: float | None = None
    mount_type: str | None = Field(default=None, alias="mountType")


InventoryDevice = InnerSpaceInventoryDevice

__all__ = [
    "InnerSpaceInventoryDevice",
    "InventoryDevice",
]
