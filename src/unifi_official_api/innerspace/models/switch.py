"""Switch models for UniFi InnerSpace API."""

from pydantic import Field

from .project import InnerSpaceBaseModel


class InnerSpaceSwitch(InnerSpaceBaseModel):
    """Switch placement entry returned by ``GET /v1/switches``."""

    id: str = Field(min_length=1)
    name: str = ""
    mac: str | None = None
    model: str | None = None
    floor_plan_id: str | None = Field(default=None, alias="floorPlanId")
    x: float | None = None
    y: float | None = None
    port_count: int | None = Field(default=None, alias="portCount")
    poe_budget: float | None = Field(default=None, alias="poeBudget")


__all__ = ["InnerSpaceSwitch"]
