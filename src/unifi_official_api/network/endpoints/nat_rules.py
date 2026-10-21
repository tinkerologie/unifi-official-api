"""NAT rules endpoint for UniFi Network API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from ...const import ENDPOINT_NAT_RULES
from ...exceptions import (
    UniFiNotFoundError,
    UniFiResponseError,
    UniFiRuleNotEditableError,
    UniFiValidationError,
)
from ...validation import sanitized_validation_fields
from ..models.nat_rule import (
    NatRule,
    is_predefined_nat_rule,
)

if TYPE_CHECKING:
    from ..client import UniFiNetworkClient

_LOGGER = logging.getLogger(__name__)


class NatRulesEndpoint:
    """
    Endpoint for custom NAT rules.

    Targets the legacy v2 controller endpoint:
    ``/proxy/network/v2/api/site/{site_name}/nat``

    This path is not in the official UniFi API. Its shape is reference-derived
    (sirkirby/unifi-mcp, hyperb1iss/unifly, ubiquiti-community/go-unifi) and was
    not observed on a live console: Network 11 answered 200 with no records on
    2026-10-12. There is no GET-by-id, so an update fetches the list, finds the
    record, toggles ``enabled`` and PUTs the full raw object to ``nat/{rule_id}``.
    X-API-Key acceptance for the PUT is unverified.
    """

    def __init__(self, client: UniFiNetworkClient) -> None:
        """Initialize the NAT Rules endpoint."""
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
            msg = "Unexpected NAT rules list response"
            raise UniFiValidationError(msg)
        return response

    def _parse_strict(self, response: Any) -> list[NatRule]:
        """Validate every record of a list answer; the first bad one raises."""
        rules: list[NatRule] = []
        for item in self._extract_strict_items(response):
            try:
                rules.append(NatRule.model_validate(item))
            except ValidationError:
                break
        else:
            return rules
        # Raised outside the handler so no validation error, which quotes the
        # record, is attached to it as context.
        msg = "Invalid NAT rule record"
        raise UniFiValidationError(msg)

    async def list_nat_rules(self, site_name: str, *, strict: bool = False) -> list[NatRule]:
        """
        List all NAT rules for a site.

        With ``strict`` (the rule export) the answer must be a list of valid
        records, otherwise ``UniFiValidationError`` is raised: nothing is
        skipped and the response body is not logged.
        """
        path = self._client.build_legacy_v2_api_path(site_name, ENDPOINT_NAT_RULES)
        if strict:
            return self._parse_strict(await self._client._get(path, log_body=False))
        response = await self._client._get(path)
        items = self._extract_items(response)

        rules: list[NatRule] = []
        for item in items:
            try:
                rules.append(NatRule.model_validate(item))
            except ValidationError as err:
                _LOGGER.debug(
                    "Skipping invalid NAT rule item (%s: %s)",
                    type(err).__name__,
                    sanitized_validation_fields(err),
                )
                continue

        return rules

    async def update_nat_rule(self, site_name: str, rule_id: str, *, enabled: bool) -> NatRule:
        """Enable or disable a NAT rule."""
        list_path = self._client.build_legacy_v2_api_path(site_name, ENDPOINT_NAT_RULES)
        items = self._extract_items(await self._client._get(list_path))
        current = next((i for i in items if (i.get("_id") or i.get("id")) == rule_id), None)
        if current is None:
            msg = f"NAT rule {rule_id} not found"
            raise UniFiNotFoundError(msg, status_code=404)

        if is_predefined_nat_rule(current):
            raise UniFiRuleNotEditableError(f"NAT rule {rule_id} is managed by the console")

        payload = dict(current)
        payload["enabled"] = enabled

        put_path = self._client.build_legacy_v2_api_path(
            site_name, f"{ENDPOINT_NAT_RULES}/{rule_id}"
        )
        put_items = self._extract_items(await self._client._put(put_path, json_data=payload))
        if put_items and (put_items[0].get("_id") or put_items[0].get("id")) == rule_id:
            return NatRule.model_validate(put_items[0])

        return NatRule.model_validate(payload)
