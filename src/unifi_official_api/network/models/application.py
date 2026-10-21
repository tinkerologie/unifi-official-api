"""Application info model for UniFi Network API."""

from pydantic import BaseModel, ConfigDict, Field


class ApplicationInfo(BaseModel):
    """Model representing UniFi Network application information."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    application_version: str = Field(alias="applicationVersion")


__all__ = ["ApplicationInfo"]
