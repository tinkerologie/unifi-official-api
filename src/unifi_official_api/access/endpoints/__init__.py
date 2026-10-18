"""Endpoint groups for the UniFi Access developer API."""

from .devices import DevicesEndpoint
from .doors import GATE_COMMANDS, DoorsEndpoint, GateCommand
from .emergency import EmergencyEndpoint
from .users import USER_STATUS_WRITES, UsersEndpoint, UserStatusWrite
from .webhooks import WebhooksEndpoint

__all__ = [
    "GATE_COMMANDS",
    "USER_STATUS_WRITES",
    "DevicesEndpoint",
    "DoorsEndpoint",
    "EmergencyEndpoint",
    "GateCommand",
    "UserStatusWrite",
    "UsersEndpoint",
    "WebhooksEndpoint",
]
