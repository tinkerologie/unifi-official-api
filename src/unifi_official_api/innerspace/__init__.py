"""UniFi InnerSpace API module."""

from __future__ import annotations

from .client import (
    MAX_ASSET_SEGMENT_LENGTH,
    UniFiInnerSpaceClient,
    is_valid_asset_segment,
)
from .endpoints import (
    AccessPointsEndpoint,
    ApplicationEndpoint,
    AssetsEndpoint,
    FloorPlansEndpoint,
    InventoryEndpoint,
    ProjectEndpoint,
    SwitchesEndpoint,
)
from .models import (
    ApplicationInfo,
    FloorPlan,
    InnerSpaceAccessPoint,
    InnerSpaceBaseModel,
    InnerSpaceFloorPlan,
    InnerSpaceInventoryDevice,
    InnerSpaceMountType,
    InnerSpacePlan,
    InnerSpaceProduct,
    InnerSpaceProject,
    InnerSpaceProjectIdentity,
    InnerSpaceSwitch,
    InventoryDevice,
    ProjectData,
    ProjectMeta,
)

__all__ = [
    "MAX_ASSET_SEGMENT_LENGTH",
    "AccessPointsEndpoint",
    "ApplicationEndpoint",
    "ApplicationInfo",
    "AssetsEndpoint",
    "FloorPlan",
    "FloorPlansEndpoint",
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
    "InventoryEndpoint",
    "ProjectData",
    "ProjectEndpoint",
    "ProjectMeta",
    "SwitchesEndpoint",
    "UniFiInnerSpaceClient",
    "is_valid_asset_segment",
]
