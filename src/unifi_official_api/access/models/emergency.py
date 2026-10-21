"""Emergency and lock-rule models for the UniFi Access developer API."""

from typing import Literal

from .common import AccessRecord

# Documented lock-rule types in the Ubiquiti UniFi Access API Reference V2.2.10
# (Section 7.10, minimum version Access 1.24.6+). ``lock_now`` is not documented
# in the official API, so it is not offered here.
LockRuleType = Literal["keep_lock", "keep_unlock", "custom", "reset", "lock_early"]
LOCK_RULE_TYPES: tuple[LockRuleType, ...] = (
    "keep_lock",
    "keep_unlock",
    "custom",
    "reset",
    "lock_early",
)


class AccessEmergencyStatus(AccessRecord):
    """
    Console-wide emergency state from ``GET /doors/settings/emergency``.

    Verified against the Ubiquiti UniFi Access API Reference V2.2.10
    (Section 7.13, minimum Access application version ``1.24.6+``) and
    live-console / vendored test payloads.
    """

    lockdown: bool | None = None
    evacuation: bool | None = None


class AccessLockRuleStatus(AccessRecord):
    """Result of ``PUT /doors/:id/lock_rule``: the rule the console applied."""

    type: str | None = None
    ended_time: int | None = None
