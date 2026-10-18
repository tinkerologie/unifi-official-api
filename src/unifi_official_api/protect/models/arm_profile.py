"""Arm profile models for UniFi Protect API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ArmSchedule(BaseModel):
    """Arm schedule entry within an arm profile."""

    id: str | None = None
    days: list[str] = Field(default_factory=list)
    start_time: str | None = Field(default=None, alias="startTime")
    end_time: str | None = Field(default=None, alias="endTime")

    model_config = {"populate_by_name": True, "extra": "allow"}


class ArmProfileSettings(BaseModel):
    """Arm profile active settings."""

    active_profile_id: str | None = Field(default=None, alias="activeProfileId")
    is_armed: bool = Field(default=False, alias="isArmed")

    model_config = {"populate_by_name": True, "extra": "allow"}


class ArmProfile(BaseModel):
    """UniFi Protect arm profile."""

    id: str
    model_key: str | None = Field(default="armProfile", alias="modelKey")
    name: str | None = None
    record_everything: bool | None = Field(default=None, alias="recordEverything")
    activation_delay: int | None = Field(default=None, alias="activationDelay")
    creator: str | None = None
    created_at: Any | None = Field(default=None, alias="createdAt")
    updated_at: Any | None = Field(default=None, alias="updatedAt")
    arm_auto_away_enabled: bool | None = Field(default=None, alias="armAutoAwayEnabled")
    bypass_Next_schedule: bool | None = Field(default=None, alias="bypassNextSchedule")
    entry_delay: int | None = Field(default=None, alias="entryDelay")
    exit_delay: int | None = Field(default=None, alias="exitDelay")
    automations: list[str | dict[str, Any]] | dict[str, Any] | None = None
    schedules: list[ArmSchedule | dict[str, Any]] | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}
