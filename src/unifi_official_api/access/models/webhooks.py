"""Webhook endpoint models for the UniFi Access developer API."""

from __future__ import annotations

from pydantic import SecretStr

from .common import AccessRecord


class AccessWebhookEndpoint(AccessRecord):
    """
    One registered webhook endpoint (minimum Access version ``2.2.10+``).

    ``secret`` signs deliveries (HMAC-SHA256 over ``<t>.<raw body>``). It is a
    ``SecretStr``, so reprs and default dumps hide it.
    """

    id: str | None = None
    endpoint: str | None = None
    name: str | None = None
    events: list[str] | None = None
    secret: SecretStr | None = None
