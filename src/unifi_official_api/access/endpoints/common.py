"""Shared helpers for UniFi Access endpoint groups."""

import re
from typing import Any

from ...exceptions import UniFiValidationError

# Access IDs are UUIDs or 12-character device MACs. They become path segments,
# so anything else is refused before a request is made.
_ID_PATTERN = re.compile(r"[0-9A-Za-z-]{1,64}")


def safe_id(identifier: Any) -> str:
    """Return an ID that is safe to place in a URL path segment."""
    if isinstance(identifier, str) and _ID_PATTERN.fullmatch(identifier):
        return identifier
    msg = "Invalid UniFi Access identifier"
    raise UniFiValidationError(msg)
