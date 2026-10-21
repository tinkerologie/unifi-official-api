"""ULP (UniFi Local Portal) user models for UniFi Protect API."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class UlpUserStatus(StrEnum):
    """Account status for a ULP user."""

    ACTIVE = "ACTIVE"
    DEACTIVATED = "DEACTIVATED"


class UlpUser(BaseModel):
    """UniFi Protect ULP (UniFi Local Portal) user account model."""

    id: str = Field(..., description="ULP user identifier")
    first_name: str = Field(..., alias="firstName", description="First name")
    last_name: str = Field(..., alias="lastName", description="Last name")
    full_name: str = Field(..., alias="fullName", description="Combined full name")
    email: str = Field(default="", description="Email address (may be empty if not set)")
    status: UlpUserStatus | str = Field(..., description="Account status")
    model_key: str = Field(default="ulpUser", alias="modelKey")

    model_config = {"populate_by_name": True, "extra": "allow"}

    @property
    def display_name(self) -> str:
        """Return display name for the ULP user."""
        return self.full_name or self.email or self.id


ULPUser = UlpUser
