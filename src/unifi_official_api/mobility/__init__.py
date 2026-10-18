"""UniFi Mobility API module."""

from __future__ import annotations

from .client import UniFiMobilityClient, is_valid_mobility_id
from .models import (
    AdminPermission,
    AdminSummary,
    DeviceLocation,
    MobilityDeviceClient,
    MobilityDeviceDetail,
    MobilityDeviceSummary,
    UpdateDeviceNameReq,
    UpdateNetworkReq,
    UpdateWirelessReq,
    WorkspaceSummary,
)

__all__ = [
    "AdminPermission",
    "AdminSummary",
    "DeviceLocation",
    "MobilityDeviceClient",
    "MobilityDeviceDetail",
    "MobilityDeviceSummary",
    "UniFiMobilityClient",
    "UpdateDeviceNameReq",
    "UpdateNetworkReq",
    "UpdateWirelessReq",
    "WorkspaceSummary",
    "is_valid_mobility_id",
]
