"""Static routes endpoint for UniFi Network API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from ...const import ENDPOINT_STATIC_ROUTES
from ...exceptions import (
    UniFiNotFoundError,
    UniFiResponseError,
    UniFiValidationError,
)
from ...validation import parse_record, sanitized_validation_fields, written_record
from ..models.static_route import StaticRoute

if TYPE_CHECKING:
    from ..client import UniFiNetworkClient

_LOGGER = logging.getLogger(__name__)


class StaticRoutesEndpoint:
    """
    Endpoint for static routes.

    Targets the classic controller endpoint:
    ``/proxy/network/api/s/{site_name}/rest/routing``

    This path is not in the official UniFi API (Network 11 returns 404 on v2
    ``/static-route``). Its shape is reference-derived (filipowm/go-unifi
    ``Routing.json``, sirkirby/unifi-network-rules) and was not observed on a
    live console: Network 11 answered 200 with no records on 2026-10-12. An
    update fetches the list, finds the record, toggles ``enabled`` and PUTs the
    full raw object to ``rest/routing/{rule_id}``. X-API-Key acceptance for the
    PUT is unverified.
    """

    def __init__(self, client: UniFiNetworkClient) -> None:
        """Initialize the Static Routes endpoint."""
        self._client = client

    def _extract_items(self, response: Any) -> list[dict[str, Any]]:
        """Extract data items from a legacy response envelope."""
        if response is None:
            return []

        if isinstance(response, dict):
            meta = response.get("meta")
            if isinstance(meta, dict) and meta.get("rc") == "error":
                msg = meta.get("msg", "UniFi Network API error")
                raise UniFiResponseError(msg, status_code=200, response_body=str(response))

            data = response.get("data", response)
            if isinstance(data, list):
                return [item for item in data if isinstance(item, dict)]
            if isinstance(data, dict):
                return [data]
            return []

        if isinstance(response, list):
            return [item for item in response if isinstance(item, dict)]

        return []

    def _extract_strict_items(self, response: Any) -> list[dict[str, Any]]:
        """
        Return the records of a list answer, or raise.

        Used by the rule export, which must not present a broken answer as a
        list of rules: the body must be a list, or a dict whose ``data`` is a
        list, and every element must be a dict. Nothing of the response is
        put in a message.
        """
        if isinstance(response, dict):
            # A classic answer says rc ok; anything else (an error, another
            # spelling, an envelope that is not a dict) is a failed read. It is
            # raised as a validation error because a response error with status
            # 200 would be classified "unsupported".
            if "meta" in response:
                meta = response["meta"]
                if not isinstance(meta, dict) or meta.get("rc") != "ok":
                    msg = "UniFi Network API did not report success"
                    raise UniFiValidationError(msg)
            response = response.get("data")
        if not isinstance(response, list) or not all(isinstance(item, dict) for item in response):
            msg = "Unexpected static routes list response"
            raise UniFiValidationError(msg)
        return response

    def _parse_strict(self, response: Any) -> list[StaticRoute]:
        """Validate every record of a list answer; the first bad one raises."""
        rules: list[StaticRoute] = []
        for item in self._extract_strict_items(response):
            try:
                rules.append(StaticRoute.model_validate(item))
            except ValidationError:
                break
        else:
            return rules
        # Raised outside the handler so no validation error, which quotes the
        # record, is attached to it as context.
        msg = "Invalid static route record"
        raise UniFiValidationError(msg)

    async def list_static_routes(
        self, site_name: str, *, strict: bool = False
    ) -> list[StaticRoute]:
        """
        List all static routes for a site.

        With ``strict`` (the rule export) the answer must be a list of valid
        records, otherwise ``UniFiValidationError`` is raised: nothing is
        skipped and the response body is not logged.
        """
        path = self._client.build_legacy_api_path(site_name, ENDPOINT_STATIC_ROUTES)
        if strict:
            return self._parse_strict(await self._client._get(path, log_body=False))
        response = await self._client._get(path)
        items = self._extract_items(response)

        rules: list[StaticRoute] = []
        for item in items:
            try:
                rules.append(StaticRoute.model_validate(item))
            except ValidationError as err:
                _LOGGER.debug(
                    "Skipping invalid static route item (%s: %s)",
                    type(err).__name__,
                    sanitized_validation_fields(err),
                )
                continue

        return rules

    async def update_static_route(
        self, site_name: str, rule_id: str, *, enabled: bool
    ) -> StaticRoute:
        """Enable or disable a static route."""
        list_path = self._client.build_legacy_api_path(site_name, ENDPOINT_STATIC_ROUTES)
        items = self._extract_items(await self._client._get(list_path))
        current = next((i for i in items if (i.get("_id") or i.get("id")) == rule_id), None)
        if current is None:
            msg = f"Static route {rule_id} not found"
            raise UniFiNotFoundError(msg, status_code=200)

        payload = dict(current)
        payload["enabled"] = enabled

        put_path = self._client.build_legacy_api_path(
            site_name, f"{ENDPOINT_STATIC_ROUTES}/{rule_id}"
        )
        put_items = self._extract_items(await self._client._put(put_path, json_data=payload))
        if put_items and (put_items[0].get("_id") or put_items[0].get("id")) == rule_id:
            written = written_record(put_items[0], StaticRoute, id_key=None)
            if written is not None:
                return written
        return parse_record(StaticRoute, payload, f"Static route {rule_id}")
