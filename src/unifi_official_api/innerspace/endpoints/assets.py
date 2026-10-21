"""Assets endpoint for UniFi InnerSpace API."""

from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING
from urllib.parse import quote

from unifi_official_api.exceptions import UniFiValidationError

if TYPE_CHECKING:
    from unifi_official_api.innerspace.client import UniFiInnerSpaceClient

MAX_ASSET_SEGMENT_LENGTH = 255


def is_valid_asset_segment(segment: str) -> bool:
    """
    Validate a decoded asset path segment (plan ID or filename).

    Accepts 1-255 characters and rejects anything that could change the
    request path: blank segments, `.`/`..`, path separators, and control
    characters (Unicode category Cc, which includes NUL).
    """
    if (
        not isinstance(segment, str)
        or not segment.strip()
        or len(segment) > MAX_ASSET_SEGMENT_LENGTH
    ):
        return False
    if segment in (".", ".."):
        return False
    return not any(ch in "/\\" or unicodedata.category(ch) == "Cc" for ch in segment)


def _validate_asset_segment(segment: str, name: str = "segment") -> str:
    """Validate and URL-quote an InnerSpace asset path segment."""
    if not isinstance(segment, str) or not is_valid_asset_segment(segment):
        msg = f"Invalid InnerSpace {name}: {segment!r}"
        raise UniFiValidationError(msg)
    return quote(segment, safe="")


class AssetsEndpoint:
    """Endpoint for ``GET /v1/assets/{planId}/{filename}``."""

    def __init__(self, client: UniFiInnerSpaceClient) -> None:
        self._client = client

    async def download_floor_plan_image(self, plan_id: str, filename: str) -> tuple[bytes, str]:
        """
        Download floor plan image binary data.

        Returns:
            Tuple of (binary_content, content_type).
        """
        if not is_valid_asset_segment(plan_id):
            msg = f"Invalid floor plan ID: {plan_id!r}"
            raise UniFiValidationError(msg)
        if not is_valid_asset_segment(filename):
            msg = f"Invalid asset filename: {filename!r}"
            raise UniFiValidationError(msg)

        quoted_plan = quote(plan_id, safe="")
        quoted_file = quote(filename, safe="")
        path = self._client.build_api_path(f"assets/{quoted_plan}/{quoted_file}")
        return await self._client._get_binary_with_content_type(path)

    async def download(self, plan_id: str, filename: str) -> bytes:
        """
        Download asset binary content.

        Raises:
            UniFiValidationError: If ``plan_id`` or ``filename`` is not a safe path segment.
            UniFiNotFoundError: If the console answers 404.
            UniFiResponseError: If the console answers any other 4xx or 5xx status.
            UniFiConnectionError: If the console cannot be reached.

        """
        content, _ = await self.download_floor_plan_image(plan_id, filename)
        return content
