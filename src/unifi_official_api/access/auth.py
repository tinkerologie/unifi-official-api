"""Bearer token authentication for the UniFi Access developer API."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, repr=False)
class AccessTokenAuth:
    """
    Access API token, sent as an ``Authorization: Bearer`` header.

    The token is created in Access > Settings > General > Advanced. It is
    separate from the UniFi Network and Protect API key, and its repr never
    shows the value.
    """

    token: str
    verify_ssl: bool = True

    def get_headers(self) -> dict[str, str]:
        """Return the bearer authorization header for an Access request."""
        return {"Authorization": f"Bearer {self.token}"}

    def __repr__(self) -> str:
        """Return a representation that hides the token."""
        return f"AccessTokenAuth(token=**REDACTED**, verify_ssl={self.verify_ssl})"
