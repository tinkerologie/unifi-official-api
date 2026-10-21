"""Fob endpoint for UniFi Protect API."""

from ..models.fob import Fob
from ._base import ProtectDeviceEndpoint


class FobsEndpoint(ProtectDeviceEndpoint[Fob]):
    """Endpoint for managing UniFi Protect key fobs."""

    _resource = "fobs"
    _model = Fob
