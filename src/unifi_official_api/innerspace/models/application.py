"""Application info model for UniFi InnerSpace API."""

from __future__ import annotations

from pydantic import Field

from .project import InnerSpaceBaseModel


class ApplicationInfo(InnerSpaceBaseModel):
    """InnerSpace application information."""

    version: str | None = Field(default=None, alias="applicationVersion")


__all__ = ["ApplicationInfo"]
