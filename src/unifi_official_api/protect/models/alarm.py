"""Alarm models for UniFi Protect API."""

from .arm_profile import ArmProfile, ArmProfileSettings, ArmSchedule
from .link_station import AlarmHub, LinkStation

__all__ = [
    "AlarmHub",
    "ArmProfile",
    "ArmProfileSettings",
    "ArmSchedule",
    "LinkStation",
]
