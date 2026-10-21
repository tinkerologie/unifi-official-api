"""Bridges endpoint for UniFi Protect API."""

from ..models.bridge import Bridge
from ._base import ProtectDeviceEndpoint


class BridgesEndpoint(ProtectDeviceEndpoint[Bridge]):
    """Endpoint for managing UniFi Protect bridges."""

    _resource = "bridges"
    _model = Bridge
