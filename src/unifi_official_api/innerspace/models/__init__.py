"""Models for UniFi InnerSpace API."""

from .access_point import InnerSpaceAccessPoint, InnerSpaceMountType
from .application import ApplicationInfo
from .floor_plan import FloorPlan, InnerSpaceFloorPlan
from .inventory import InnerSpaceInventoryDevice, InventoryDevice
from .project import (
    InnerSpaceBaseModel,
    InnerSpacePlan,
    InnerSpaceProduct,
    InnerSpaceProject,
    InnerSpaceProjectIdentity,
    ProjectData,
    ProjectMeta,
)
from .switch import InnerSpaceSwitch

__all__ = [
    "ApplicationInfo",
    "FloorPlan",
    "InnerSpaceAccessPoint",
    "InnerSpaceBaseModel",
    "InnerSpaceFloorPlan",
    "InnerSpaceInventoryDevice",
    "InnerSpaceMountType",
    "InnerSpacePlan",
    "InnerSpaceProduct",
    "InnerSpaceProject",
    "InnerSpaceProjectIdentity",
    "InnerSpaceSwitch",
    "InventoryDevice",
    "ProjectData",
    "ProjectMeta",
]
