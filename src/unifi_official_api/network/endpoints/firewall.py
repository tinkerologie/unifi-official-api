"""Firewall endpoint for UniFi Network API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from ...exceptions import UniFiNotFoundError, UniFiValidationError
from ...validation import (
    created_record,
    parse_records,
    require_record,
    response_record,
    sanitized_validation_fields,
    written_record,
)
from ..models import FirewallRule, FirewallZone
from ..models.firewall import (
    FirewallPolicyOrdering,
    OrderedFirewallPolicyIds,
)

if TYPE_CHECKING:
    from ..client import UniFiNetworkClient


_LOGGER = logging.getLogger(__name__)


class FirewallEndpoint:
    """Endpoint for managing firewall rules and zones."""

    def __init__(self, client: UniFiNetworkClient) -> None:
        """
        Initialize the firewall endpoint.

        Args:
            client: The UniFi Network client.

        """
        self._client = client

    async def list_zones(
        self,
        site_id: str,
        *,
        offset: int | None = None,
        limit: int | None = None,
        filter_str: str | None = None,
    ) -> list[FirewallZone]:
        """
        List all firewall zones.

        Args:
            site_id: The site ID.
            offset: Number of items to skip (pagination).
            limit: Maximum number of items to return.
            filter_str: Filter query string using API filter syntax.
                Example: "name.like('Internal*')" or "and(name.isNotNull(), id.eq('zone-1'))"

        Returns:
            List of firewall zones.

        Raises:
            UniFiResponseError: If an item in the response fails validation.

        """
        params: dict[str, Any] = {}
        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = limit
        if filter_str:
            params["filter"] = filter_str

        path = self._client.build_api_path(f"/sites/{site_id}/firewall/zones")
        response = await self._client._get(path, params=params if params else None)

        if response is None:
            return []

        data = response.get("data", response) if isinstance(response, dict) else response
        if isinstance(data, list):
            return parse_records(FirewallZone, data, "Firewall zone")
        return []

    async def get_zone(self, site_id: str, zone_id: str) -> FirewallZone:
        """
        Get a specific firewall zone.

        Args:
            site_id: The site ID.
            zone_id: The zone ID.

        Returns:
            The firewall zone.

        Raises:
            UniFiNotFoundError: If the response holds no firewall zone.
            UniFiResponseError: If the firewall zone in the response fails validation.

        """
        path = self._client.build_api_path(f"/sites/{site_id}/firewall/zones/{zone_id}")
        return require_record(
            await self._client._get(path), FirewallZone, f"Firewall zone {zone_id}", id_key=None
        )

    async def create_zone(
        self,
        site_id: str,
        *,
        name: str,
        **kwargs: Any,
    ) -> FirewallZone:
        """
        Create a custom firewall zone.

        Args:
            site_id: The site ID.
            name: Zone name.
            **kwargs: Additional parameters.

        Returns:
            The created firewall zone.

        Raises:
            UniFiResponseError: If the console accepted the request but the response
                holds no valid firewall zone. The firewall zone may have been created.

        """
        path = self._client.build_api_path(f"/sites/{site_id}/firewall/zones")
        data: dict[str, Any] = {"name": name}
        data.update(kwargs)

        response = await self._client._post(path, json_data=data)
        return created_record(response, FirewallZone, "Firewall zone", id_key=None)

    async def update_zone(
        self,
        site_id: str,
        zone_id: str,
        **kwargs: Any,
    ) -> FirewallZone:
        """
        Update a firewall zone.

        Args:
            site_id: The site ID.
            zone_id: The zone ID.
            **kwargs: Parameters to update.

        Returns:
            The updated firewall zone.

        Raises:
            UniFiNotFoundError: If the follow-up ``get_zone()`` finds no firewall zone.
            UniFiResponseError: If the follow-up ``get_zone()`` response fails validation.

        """
        path = self._client.build_api_path(f"/sites/{site_id}/firewall/zones/{zone_id}")
        written = written_record(
            await self._client._put(path, json_data=kwargs), FirewallZone, id_key=None
        )
        if written is not None:
            return written
        return await self.get_zone(site_id, zone_id)

    async def delete_zone(self, site_id: str, zone_id: str) -> bool:
        """
        Delete a custom firewall zone.

        Args:
            site_id: The site ID.
            zone_id: The zone ID.

        Returns:
            True if successful.

        """
        path = self._client.build_api_path(f"/sites/{site_id}/firewall/zones/{zone_id}")
        await self._client._delete(path)
        return True

    async def list_rules(
        self,
        site_id: str,
        *,
        offset: int | None = None,
        limit: int | None = None,
        filter_str: str | None = None,
        strict: bool = False,
    ) -> list[FirewallRule]:
        """
        List all firewall rules.

        When called without explicit offset/limit, automatically paginates
        to retrieve all rules.

        Args:
            site_id: The site ID.
            offset: Number of items to skip (pagination).
            limit: Maximum number of items to return.
            filter_str: Filter query string using API filter syntax.
                Example: "action.eq('drop')" or "and(name.isNotNull(), enabled.eq(true))"
            strict: Used by the rule export. Every page must be a list of valid
                rules, otherwise ``UniFiValidationError`` is raised, and the
                response bodies are not logged. Without it, a rule that fails
                validation is skipped and logged at debug level by field name.

        Returns:
            List of firewall rules.

        """
        path = self._client.build_api_path(f"/sites/{site_id}/firewall/policies")
        parse = self._parse_rules_strict if strict else self._parse_rules_response
        get_options: dict[str, Any] = {"log_body": False} if strict else {}

        # When caller supplies explicit pagination, honour it as a single request.
        if offset is not None or limit is not None:
            params: dict[str, Any] = {}
            if offset is not None:
                params["offset"] = offset
            if limit is not None:
                params["limit"] = limit
            if filter_str:
                params["filter"] = filter_str
            return parse(
                await self._client._get(path, params=params if params else None, **get_options)
            )

        # Auto-paginate to retrieve all rules.
        all_rules: list[FirewallRule] = []
        current_offset = 0
        page_size = 200

        while True:
            params = {"offset": current_offset, "limit": page_size}
            if filter_str:
                params["filter"] = filter_str

            response = await self._client._get(path, params=params, **get_options)
            rules = parse(response)
            all_rules.extend(rules)

            # Check if there are more pages.
            total = response.get("totalCount") if isinstance(response, dict) else None
            if total is None or current_offset + page_size >= total:
                break
            current_offset += page_size

        if strict:
            # Every page was valid, but the pages must also add up: the console
            # reports how many policies there are, and a policy added or removed
            # between two page requests shifts the offsets.
            msg = "Incomplete firewall policy list"
            if total is not None and len(all_rules) != total:
                raise UniFiValidationError(msg)
            if total is None and len(rules) >= page_size:
                raise UniFiValidationError(msg)
            if len({rule.id for rule in all_rules}) != len(all_rules):
                raise UniFiValidationError(msg)

        return all_rules

    @staticmethod
    def _parse_rules_response(response: Any) -> list[FirewallRule]:
        """Parse a firewall policies API response into a list of rules."""
        if response is None:
            return []
        data = response.get("data", response) if isinstance(response, dict) else response
        if isinstance(data, list):
            rules: list[FirewallRule] = []
            for item in data:
                try:
                    rules.append(FirewallRule.model_validate(item))
                except ValidationError as err:
                    _LOGGER.debug(
                        "Skipping invalid firewall policy item (%s: %s)",
                        type(err).__name__,
                        sanitized_validation_fields(err),
                    )
            return rules
        return []

    @staticmethod
    def _parse_rules_strict(response: Any) -> list[FirewallRule]:
        """Parse one page of firewall policies; anything but valid rules raises."""
        data = response.get("data") if isinstance(response, dict) else response
        if not isinstance(data, list) or not all(isinstance(i, dict) for i in data):
            msg = "Unexpected firewall policy list response"
            raise UniFiValidationError(msg)
        rules: list[FirewallRule] = []
        for item in data:
            try:
                rules.append(FirewallRule.model_validate(item))
            except ValidationError:
                break
        else:
            return rules
        # Raised outside the handler so no validation error, which quotes the
        # record, is attached to it as context.
        msg = "Invalid firewall policy record"
        raise UniFiValidationError(msg)

    async def get_rule(self, site_id: str, rule_id: str) -> FirewallRule:
        """
        Get a specific firewall rule.

        Args:
            site_id: The site ID.
            rule_id: The rule ID.

        Returns:
            The firewall rule.

        Raises:
            UniFiNotFoundError: If the response holds no firewall rule.
            UniFiResponseError: If the firewall rule in the response fails validation.

        """
        path = self._client.build_api_path(f"/sites/{site_id}/firewall/policies/{rule_id}")
        return require_record(
            await self._client._get(path), FirewallRule, f"Firewall rule {rule_id}", id_key=None
        )

    async def create_rule(
        self,
        site_id: str,
        *,
        name: str,
        action: str | dict[str, Any] = "drop",
        protocol: str = "all",
        source_zone_id: str | None = None,
        destination_zone_id: str | None = None,
        **kwargs: Any,
    ) -> FirewallRule:
        """
        Create a new firewall rule.

        Args:
            site_id: The site ID.
            name: Rule name.
            action: Legacy action name or pre-built ALLOW/BLOCK/REJECT object.
                ALLOW defaults allowReturnTraffic to False if omitted.
            protocol: Only all is supported; use ipProtocolScope for other protocols.
            source_zone_id: Source zone ID.
            destination_zone_id: Destination zone ID.
            **kwargs: Additional parameters, sent as given in camelCase, such as
                ``reportFlowEnabled=False``. The console defaults
                ``reportFlowEnabled`` to true when it is omitted.

        Returns:
            The created firewall rule.

        Raises:
            ValueError: If the action, protocol or zones are invalid; no request is made.
            UniFiResponseError: If the console accepted the request but the response
                holds no valid firewall rule. The rule may have been created.

        """
        path = self._client.build_api_path(f"/sites/{site_id}/firewall/policies")
        action_types = {
            "ACCEPT": "ALLOW",
            "ALLOW": "ALLOW",
            "DROP": "BLOCK",
            "DENY": "BLOCK",
            "BLOCK": "BLOCK",
            "REJECT": "REJECT",
        }
        action_value = action.get("type") if isinstance(action, dict) else action
        action_type = (
            action_types.get(action_value.upper()) if isinstance(action_value, str) else None
        )
        if action_type is None:
            msg = f"Unsupported firewall action: {action_value}"
            raise ValueError(msg)
        if protocol != "all" and "ipProtocolScope" not in kwargs:
            msg = "Use ipProtocolScope for protocols other than all"
            raise ValueError(msg)
        action_data: dict[str, Any] = dict(action) if isinstance(action, dict) else {}
        action_data["type"] = action_type
        if action_type == "ALLOW":
            action_data.setdefault("allowReturnTraffic", False)
            if not isinstance(action_data["allowReturnTraffic"], bool):
                msg = "ALLOW allowReturnTraffic must be a boolean"
                raise ValueError(msg)
        data: dict[str, Any] = {
            "name": name,
            "action": action_data,
            "source": {"zoneId": source_zone_id},
            "destination": {"zoneId": destination_zone_id},
            "ipProtocolScope": {"ipVersion": "IPV4"},
            "enabled": True,
            "loggingEnabled": False,
        }
        data.update(kwargs)
        for field in ("source", "destination"):
            zone = data[field]
            if not isinstance(zone, dict) or not zone.get("zoneId"):
                msg = f"A {field} zoneId is required"
                raise ValueError(msg)

        response = await self._client._post(path, json_data=data)
        return created_record(response, FirewallRule, "Firewall rule", id_key=None)

    @staticmethod
    def _extract_rule_payload(
        response: dict[str, Any] | list[Any] | None,
    ) -> dict[str, Any] | None:
        """Extract a firewall rule payload from API responses."""
        record = response_record(response, id_key=None)
        return dict(record) if record is not None else None

    async def update_rule(
        self,
        site_id: str,
        rule_id: str,
        **kwargs: Any,
    ) -> FirewallRule:
        """
        Update a firewall rule.

        Full policy updates require a complete policy document via PUT.
        Use ``patch_rule`` for the partial update the spec supports
        (``loggingEnabled`` and ``reportFlowEnabled``).

        Args:
            site_id: The site ID.
            rule_id: The rule ID.
            **kwargs: Parameters to update, in camelCase, such as
                ``reportFlowEnabled=False``. Fields left out keep their current
                values.

        Returns:
            The updated firewall rule.

        Raises:
            UniFiNotFoundError: If the current rule read, or the follow-up
                ``get_rule()`` after a ``PUT`` acknowledged without a valid rule,
                holds no rule.
            UniFiResponseError: If the follow-up ``get_rule()`` response fails
                validation.

        """
        path = self._client.build_api_path(f"/sites/{site_id}/firewall/policies/{rule_id}")
        current_payload = self._extract_rule_payload(await self._client._get(path))
        if current_payload is None:
            msg = f"Firewall rule {rule_id} not found"
            raise UniFiNotFoundError(msg, status_code=200)

        # Strip read-only fields that the PUT endpoint rejects.
        for key in ("id", "index", "metadata"):
            current_payload.pop(key, None)
        current_payload.update(kwargs)

        response = await self._client._put(path, json_data=current_payload)
        written = written_record(response, FirewallRule, id_key=None)
        if written is not None:
            return written
        return await self.get_rule(site_id, rule_id)

    async def delete_rule(self, site_id: str, rule_id: str) -> bool:
        """
        Delete a firewall rule.

        Args:
            site_id: The site ID.
            rule_id: The rule ID.

        Returns:
            True if successful.

        """
        path = self._client.build_api_path(f"/sites/{site_id}/firewall/policies/{rule_id}")
        await self._client._delete(path)
        return True

    async def patch_rule(
        self,
        site_id: str,
        rule_id: str,
        *,
        logging_enabled: bool | None = None,
        report_flow_enabled: bool | None = None,
    ) -> FirewallRule:
        """
        Patch a firewall rule's loggingEnabled and reportFlowEnabled.

        These are the only fields the spec patches; only the arguments that are
        not None are sent. Use ``update_rule`` for any other change.

        Args:
            site_id: The site ID.
            rule_id: The rule ID.
            logging_enabled: Whether logging is enabled for this policy.
            report_flow_enabled: Whether Insights Flows reports traffic matched by
                this policy. The console ignores it for the predefined Allow Return
                Traffic policies and the other predefined policies it never reports.

        Returns:
            The updated firewall rule.

        Raises:
            ValueError: If neither field is passed; no request is made.
            UniFiNotFoundError: If the follow-up ``get_rule()`` finds no firewall rule.
            UniFiResponseError: If the follow-up ``get_rule()`` response fails validation.

        """
        data: dict[str, bool] = {}
        if logging_enabled is not None:
            data["loggingEnabled"] = logging_enabled
        if report_flow_enabled is not None:
            data["reportFlowEnabled"] = report_flow_enabled
        if not data:
            msg = "No firewall rule fields to patch"
            raise ValueError(msg)

        path = self._client.build_api_path(f"/sites/{site_id}/firewall/policies/{rule_id}")
        written = written_record(
            await self._client._patch(path, json_data=data), FirewallRule, id_key=None
        )
        if written is not None:
            return written
        return await self.get_rule(site_id, rule_id)

    async def get_policy_ordering(
        self,
        site_id: str,
        *,
        source_firewall_zone_id: str,
        destination_firewall_zone_id: str,
    ) -> FirewallPolicyOrdering:
        """
        Get firewall policy ordering for a zone pair.

        Args:
            site_id: The site ID.
            source_firewall_zone_id: The source firewall zone ID.
            destination_firewall_zone_id: The destination firewall zone ID.

        Returns:
            The policy ordering configuration.

        Raises:
            UniFiNotFoundError: If the response holds no policy ordering.
            UniFiResponseError: If the policy ordering in the response fails validation.

        """
        params = {
            "sourceFirewallZoneId": source_firewall_zone_id,
            "destinationFirewallZoneId": destination_firewall_zone_id,
        }
        path = self._client.build_api_path(f"/sites/{site_id}/firewall/policies/ordering")
        return require_record(
            await self._client._get(path, params=params),
            FirewallPolicyOrdering,
            "Firewall policy ordering",
            id_key=None,
        )

    async def update_policy_ordering(
        self,
        site_id: str,
        *,
        source_firewall_zone_id: str,
        destination_firewall_zone_id: str,
        ordered_firewall_policy_ids: dict[str, list[str]] | OrderedFirewallPolicyIds,
    ) -> FirewallPolicyOrdering:
        """
        Update firewall policy ordering for a zone pair.

        Args:
            site_id: The site ID.
            source_firewall_zone_id: The source firewall zone ID.
            destination_firewall_zone_id: The destination firewall zone ID.
            ordered_firewall_policy_ids: Ordered policy IDs around system rules.

        Returns:
            The updated policy ordering configuration.

        Raises:
            ValueError: If a dict ordering lacks either list; no request is made.
            UniFiNotFoundError: If the follow-up ``get_policy_ordering()`` finds no ordering.
            UniFiResponseError: If the follow-up ``get_policy_ordering()`` response fails
                validation.

        """
        params = {
            "sourceFirewallZoneId": source_firewall_zone_id,
            "destinationFirewallZoneId": destination_firewall_zone_id,
        }
        if isinstance(ordered_firewall_policy_ids, dict):
            ordered_firewall_policy_ids = OrderedFirewallPolicyIds.model_validate(
                ordered_firewall_policy_ids.get(
                    "orderedFirewallPolicyIds", ordered_firewall_policy_ids
                )
            )
            # The PUT replaces the whole ordering, so a list the caller left
            # out must not be sent as the model's empty default.
            if not {"before_system_defined", "after_system_defined"}.issubset(
                ordered_firewall_policy_ids.model_fields_set
            ):
                msg = (
                    "ordered_firewall_policy_ids needs both beforeSystemDefined "
                    "and afterSystemDefined"
                )
                raise ValueError(msg)
        # Only the two spec fields; the model allows extra keys on input.
        payload = ordered_firewall_policy_ids.model_dump(
            by_alias=True,
            include={"before_system_defined", "after_system_defined"},
        )

        data = {
            "orderedFirewallPolicyIds": payload,
        }
        path = self._client.build_api_path(f"/sites/{site_id}/firewall/policies/ordering")
        written = written_record(
            await self._client._put(path, json_data=data, params=params),
            FirewallPolicyOrdering,
            id_key=None,
        )
        if written is not None:
            return written
        return await self.get_policy_ordering(
            site_id,
            source_firewall_zone_id=source_firewall_zone_id,
            destination_firewall_zone_id=destination_firewall_zone_id,
        )
