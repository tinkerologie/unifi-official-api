"""Pydantic models for UniFi Mobility API."""

from .client import MobilityDeviceClient
from .config import UpdateDeviceNameReq, UpdateNetworkReq, UpdateWirelessReq
from .device import DeviceLocation, MobilityDeviceDetail, MobilityDeviceSummary
from .workspace import AdminPermission, AdminSummary, WorkspaceSummary

__all__ = [
    "AdminPermission",
    "AdminSummary",
    "DeviceLocation",
    "MobilityDeviceClient",
    "MobilityDeviceDetail",
    "MobilityDeviceSummary",
    "UpdateDeviceNameReq",
    "UpdateNetworkReq",
    "UpdateWirelessReq",
    "WorkspaceSummary",
]
