"""User models for UniFi Protect API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .ulp_user import ULPUser, UlpUser, UlpUserStatus


class UserGroup(BaseModel):
    """Permission group associated with a UniFi Protect user."""

    id: str
    name: str | None = None
    permissions: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True, "extra": "allow"}


class User(BaseModel):
    """UniFi Protect user account model."""

    id: str = Field(..., description="User primary key")
    name: str = Field(..., description="Display name")
    first_name: str | None = Field(default=None, alias="firstName", description="First name")
    last_name: str | None = Field(default=None, alias="lastName", description="Last name")
    email: str | None = Field(default=None, description="Email address")
    ucore_user_id: str | None = Field(
        default=None,
        alias="ucoreUserId",
        description="UniFi OS (UCore) user ID for cross-referencing with ULP users",
    )
    model_key: str = Field(default="user", alias="modelKey")

    model_config = {"populate_by_name": True, "extra": "allow"}

    @property
    def display_name(self) -> str:
        """Return display name for the user."""
        return self.name or self.email or self.id


ProtectUser = User

__all__ = [
    "ProtectUser",
    "ULPUser",
    "UlpUser",
    "UlpUserStatus",
    "User",
    "UserGroup",
]
