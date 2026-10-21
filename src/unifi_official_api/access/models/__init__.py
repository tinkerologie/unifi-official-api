"""Tolerant models for UniFi Access developer API payloads."""

from __future__ import annotations

from .common import AccessRecord, parse_record, parse_records
from .devices import AccessDevice
from .doors import AccessDoor, DoorLockRelayStatus, DoorPositionStatus
from .emergency import (
    LOCK_RULE_TYPES,
    AccessEmergencyStatus,
    AccessLockRuleStatus,
    LockRuleType,
)
from .users import (
    ACCESS_USER_STATUSES,
    WRITABLE_USER_STATUSES,
    AccessPinCredential,
    AccessUser,
    AccessUserStatus,
)
from .webhooks import AccessWebhookEndpoint

__all__ = [
    "ACCESS_USER_STATUSES",
    "LOCK_RULE_TYPES",
    "WRITABLE_USER_STATUSES",
    "AccessDevice",
    "AccessDoor",
    "AccessEmergencyStatus",
    "AccessLockRuleStatus",
    "AccessPinCredential",
    "AccessRecord",
    "AccessUser",
    "AccessUserStatus",
    "AccessWebhookEndpoint",
    "DoorLockRelayStatus",
    "DoorPositionStatus",
    "LockRuleType",
    "parse_record",
    "parse_records",
]
