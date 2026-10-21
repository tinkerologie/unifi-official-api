"""Policy-Based Route (Traffic Route) endpoint for UniFi Network API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from ...const import ENDPOINT_TRAFFIC_ROUTES
from ...exceptions import (
    UniFiNotFoundError,
    UniFiResponseError,
    UniFiValidationError,
)
from ...validation import parse_record, sanitized_validation_fields, written_record
from ..models.routes import PolicyBasedRoute

if TYPE_CHECKING:
    from ..client import UniFiNetworkClient

_LOGGER = logging.getLogger(__name__)


class RoutesEndpoint:
    """
    Endpoint for managing Policy-Based Routes (Traffic Routes).

    Targets the private controller endpoint:
    ``/proxy/network/v2/api/site/{site_name}/trafficroutes``
    """

    def __init__(self, client: UniFiNetworkClient) -> None:
        """
        Initialize the Routes endpoint.

        Args:
            client: The UniFi Network client instance.

        """
        self._client = client

    def _extract_routes_list(self, response: Any) -> list[dict[str, Any]]:
        """
        Extract the list of route dictionaries from a response envelope.

        The UniFi API may return either a list or a dictionary with 'data'
        key.
        """
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

    def _extract_strict_routes(self, response: Any) -> list[dict[str, Any]]:
        """
        Return the records of a list answer, or raise.

        Used by the rule export, which must not present a broken answer as a
        list of routes: the body must be a list, or a dict whose ``data`` is a
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
            msg = "Unexpected policy-based route list response"
            raise UniFiValidationError(msg)
        return response

    def _parse_strict_routes(self, response: Any) -> list[PolicyBasedRoute]:
        """Validate every record of a list answer; the first bad one raises."""
        routes: list[PolicyBasedRoute] = []
        for item in self._extract_strict_routes(response):
            try:
                routes.append(PolicyBasedRoute.model_validate(item))
            except Exception:
                break
        else:
            return routes
        # Raised outside the handler so no validation error, which quotes the
        # record, is attached to it as context.
        msg = "Invalid policy-based route record"
        raise UniFiValidationError(msg)

    async def list_routes(
        self, site_name: str = "default", *, strict: bool = False
    ) -> list[PolicyBasedRoute]:
        """
        Get all policy-based routes (traffic routes) for a site.

        Args:
            site_name: The UniFi classic site name (default: "default").
            strict: Used by the rule export. The answer must be a list of valid
                records, otherwise ``UniFiValidationError`` is raised: nothing
                is skipped and the response body is not logged.

        Returns:
            List of PolicyBasedRoute models.

        """
        path = self._client.build_legacy_v2_api_path(site_name, ENDPOINT_TRAFFIC_ROUTES)
        if strict:
            return self._parse_strict_routes(await self._client._get(path, log_body=False))
        response = await self._client._get(path)
        items: list[dict[str, Any]] = self._extract_routes_list(response)

        routes: list[PolicyBasedRoute] = []
        for item in items:
            try:
                routes.append(PolicyBasedRoute.model_validate(item))
            except Exception as err:
                _LOGGER.debug(
                    "Skipping invalid policy-based route item (%s: %s)",
                    type(err).__name__,
                    sanitized_validation_fields(err)
                    if isinstance(err, ValidationError)
                    else "no field details",
                )
                continue

        return routes

    async def get_route(self, site_name: str, route_id: str) -> PolicyBasedRoute:
        """
        Get a specific policy-based route by ID.

        Args:
            site_name: The UniFi classic site name.
            route_id: The ID of the policy-based route.

        Returns:
            The PolicyBasedRoute model.

        Raises:
            UniFiNotFoundError: If neither the route read nor the route listing holds
                the route.
            UniFiResponseError: If the route found fails validation.

        """
        path = self._client.build_legacy_v2_api_path(
            site_name, f"{ENDPOINT_TRAFFIC_ROUTES}/{route_id}"
        )
        response = await self._client._get(path)
        items: list[dict[str, Any]] = self._extract_routes_list(response)
        record = items[0] if items else await self._find_route_record(site_name, route_id)
        if record is None:
            msg = f"Policy-Based Route {route_id} not found"
            raise UniFiNotFoundError(msg, status_code=200)
        return parse_record(PolicyBasedRoute, record, f"Policy-Based Route {route_id}")

    async def _find_route_record(self, site_name: str, route_id: str) -> dict[str, Any] | None:
        """
        Return the raw record of a route from the route listing, or None.

        The raw record is searched, not ``list_routes()``, which skips a record
        that fails validation: that route exists and must not read as missing.
        """
        path = self._client.build_legacy_v2_api_path(site_name, ENDPOINT_TRAFFIC_ROUTES)
        for item in self._extract_routes_list(await self._client._get(path)):
            if (item.get("id") or item.get("_id")) == route_id:
                return item
        return None

    async def update_route(
        self,
        site_name: str,
        route_id: str,
        *,
        enabled: bool | None = None,
        **kwargs: Any,
    ) -> PolicyBasedRoute:
        """
        Update a policy-based route.

        Fetches the current route object, modifies the requested fields,
        and PUTs the full object back to the UniFi API.

        Args:
            site_name: The UniFi classic site name.
            route_id: The ID of the policy-based route.
            enabled: Set enabled state (True/False).
            **kwargs: Additional route fields to update.

        Returns:
            The updated PolicyBasedRoute model.

        Raises:
            UniFiNotFoundError: If the route listing holds no route with this ID, or
                the follow-up ``get_route()`` after a ``PUT`` acknowledged without a
                valid route finds none.
            UniFiResponseError: If the follow-up ``get_route()`` finds a route that
                fails validation.

        """
        current_payload = await self._find_route_record(site_name, route_id)
        if current_payload is None:
            msg = f"Policy-Based Route {route_id} not found"
            raise UniFiNotFoundError(msg, status_code=200)

        current_payload = dict(current_payload)
        if enabled is not None:
            current_payload["enabled"] = enabled

        current_payload.update(kwargs)

        put_path = self._client.build_legacy_v2_api_path(
            site_name, f"{ENDPOINT_TRAFFIC_ROUTES}/{route_id}"
        )
        put_response = await self._client._put(put_path, json_data=current_payload)
        put_items: list[dict[str, Any]] = self._extract_routes_list(put_response)
        if put_items and (put_items[0].get("id") or put_items[0].get("_id")) == route_id:
            written = written_record(put_items[0], PolicyBasedRoute, id_key=None)
            if written is not None:
                return written
        return await self.get_route(site_name, route_id)
