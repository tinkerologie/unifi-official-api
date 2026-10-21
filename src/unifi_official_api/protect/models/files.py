"""File and stream models for UniFi Protect API."""

from enum import StrEnum

from pydantic import BaseModel, Field


class FileType(StrEnum):
    """Asset file types supported by Protect."""

    ANIMATIONS = "animations"
    SOUNDS = "sounds"


class DeviceFile(BaseModel):
    """Device asset file model."""

    name: str = Field(..., description="Internal file name")
    type: FileType = Field(default=FileType.ANIMATIONS, description="File type")
    original_name: str | None = Field(default=None, alias="originalName")
    path: str | None = Field(default=None, description="File path")

    model_config = {"populate_by_name": True, "extra": "allow"}


class RTSPSStream(BaseModel):
    """RTSPS stream URLs by quality level."""

    high: str | None = Field(None, description="High quality RTSPS URL")
    medium: str | None = Field(None, description="Medium quality RTSPS URL")
    low: str | None = Field(None, description="Low quality RTSPS URL")
    package: str | None = Field(None, description="Package camera RTSPS URL")

    model_config = {"populate_by_name": True, "extra": "allow"}

    @property
    def available_qualities(self) -> list[str]:
        """Get list of quality levels that have active streams."""
        qualities: list[str] = []
        for q in ("high", "medium", "low", "package"):
            if getattr(self, q) is not None:
                qualities.append(q)
        return qualities

    def get_url(self, quality: str = "high") -> str | None:
        """Get RTSPS URL for the specified quality.

        Args:
            quality: Stream quality ("high", "medium", "low", "package").

        Returns:
            The RTSPS URL for the quality, or None if not available.
        """
        return getattr(self, quality, None)


class TalkbackSession(BaseModel):
    """Talkback session details for two-way audio."""

    url: str = Field(..., description="RTP/AVP streaming URL")
    codec: str = Field("opus", description="Audio codec (e.g. opus, aac)")
    sampling_rate: int = Field(24000, alias="samplingRate", description="Sampling rate in Hz")
    bits_per_sample: int = Field(16, alias="bitsPerSample", description="Bits per audio sample")

    model_config = {"populate_by_name": True, "extra": "allow"}


class ApplicationInfo(BaseModel):
    """UniFi Protect application metadata."""

    application_version: str = Field(
        ..., alias="applicationVersion", description="Protect application version"
    )

    model_config = {"populate_by_name": True, "extra": "allow"}
