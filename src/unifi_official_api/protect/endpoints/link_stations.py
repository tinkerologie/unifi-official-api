"""Link station endpoint for UniFi Protect API."""

from ..models.bridge import LinkStation
from ._base import ProtectDeviceEndpoint


class LinkStationsEndpoint(ProtectDeviceEndpoint[LinkStation]):
    """Endpoint for managing UniFi Protect link stations."""

    _resource = "link-stations"
    _model = LinkStation
