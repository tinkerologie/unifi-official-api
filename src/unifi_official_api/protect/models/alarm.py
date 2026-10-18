"""Alarm models for UniFi Protect API."""

from __future__ import annotations

from .arm_profile import ArmProfile, ArmProfileSettings, ArmSchedule
from .link_station import AlarmHub, LinkStation

__all__ = [
    "AlarmHub",
    "ArmProfile",
    "ArmProfileSettings",
    "ArmSchedule",
    "LinkStation",
]
