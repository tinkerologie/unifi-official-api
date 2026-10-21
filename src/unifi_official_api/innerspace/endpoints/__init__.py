"""Endpoints for UniFi InnerSpace API."""

from .access_points import AccessPointsEndpoint
from .application import ApplicationEndpoint
from .assets import (
    MAX_ASSET_SEGMENT_LENGTH,
    AssetsEndpoint,
    _validate_asset_segment,
    is_valid_asset_segment,
)
from .floor_plans import FloorPlansEndpoint
from .inventory import InventoryEndpoint
from .project import ProjectEndpoint
from .switches import SwitchesEndpoint

__all__ = [
    "MAX_ASSET_SEGMENT_LENGTH",
    "AccessPointsEndpoint",
    "ApplicationEndpoint",
    "AssetsEndpoint",
    "FloorPlansEndpoint",
    "InventoryEndpoint",
    "ProjectEndpoint",
    "SwitchesEndpoint",
    "_validate_asset_segment",
    "is_valid_asset_segment",
]
