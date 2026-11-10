"""Statistics endpoint for UniFi Network API."""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING, Any, Literal

from ...exceptions import UniFiResponseError
from ...validation import parse_record, parse_records
from ..models.stats import StatisticsSource, StatsSeries

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ..client import UniFiNetworkClient

VALID_PERIODS: frozenset[str] = frozenset({"HOUR", "DAY", "WEEK", "MONTH"})
DEFAULT_STATS_VALUES: tuple[str, ...] = ("rxBytes", "txBytes")

_SCHEMA_RE = re.compile(r"[A-Za-z0-9_]+")
_SITE_ID_RE = re.compile(r"[A-Za-z0-9_-]+")
_VALUE_RE = re.compile(r"[A-Za-z0-9_]+")


class StatsEndpoint:
    """
    Endpoint for querying controller-wide Network 11 statistics.

    Provides access to the Network 11 statistics engine endpoints:
    - GET /proxy/network/v2/api/stats/source
    - GET /proxy/network/v2/api/stats/recent/series
    """

    def __init__(self, client: UniFiNetworkClient) -> None:
        """Initialize the Stats endpoint."""
        self._client = client

    async def get_source(self, *, expected_unsupported: bool = True) -> StatisticsSource:
        """
        Query the active statistics engine source mode.

        Args:
            expected_unsupported: Whether a non-JSON 2xx response is an
                expected unsupported-endpoint signal.

        Returns:
            StatisticsSource indicating "LEGACY" or "MODERN".

        Raises:
            UniFiAuthenticationError: If authentication fails.
            UniFiResponseError: If the controller returns an unexpected payload.

        """
        path = self._client.build_legacy_v2_global_api_path("/stats/source")
        response = await self._client._get(
            path,
            expected_unsupported=expected_unsupported,
        )
        return parse_record(StatisticsSource, response, "statistics source")

    async def get_recent_series(
        self,
        *,
        schema: str,
        site_id: str,
        period: Literal["HOUR", "DAY", "WEEK", "MONTH"],
        end_ms: int,
        values: Sequence[str] = DEFAULT_STATS_VALUES,
        expected_unsupported: bool = True,
    ) -> list[StatsSeries]:
        """
        Fetch recent statistics series for a schema and site.

        Args:
            schema: The statistics schema name (e.g. "wanBySite").
            site_id: The controller's internal site UUID.
            period: Aggregation window period ("HOUR", "DAY",
                "WEEK", or "MONTH").
            end_ms: End timestamp in milliseconds since epoch.
            values: Attribute field names to project (defaults to
                ("rxBytes", "txBytes")).
            expected_unsupported: Whether a non-JSON 2xx response is an
                expected unsupported-endpoint signal.

        Returns:
            List of validated StatsSeries instances.

        Raises:
            ValueError: If parameters fail validation before request.
            UniFiAuthenticationError: If authentication fails (401/403).
            UniFiResponseError: If the controller returns a malformed response.

        """
        if period not in VALID_PERIODS:
            msg = f"Unsupported period {period!r}; expected one of {sorted(VALID_PERIODS)}"
            raise ValueError(msg)

        if isinstance(end_ms, bool) or not (
            isinstance(end_ms, int)
            or (isinstance(end_ms, float) and math.isfinite(end_ms) and end_ms.is_integer())
        ):
            msg = "end_ms must be an integer millisecond timestamp"
            raise ValueError(msg)
        int_end = int(end_ms)
        if int_end <= 0:
            msg = "end_ms must be a positive integer millisecond timestamp"
            raise ValueError(msg)

        if not isinstance(schema, str) or not _SCHEMA_RE.fullmatch(schema):
            msg = f"Invalid schema identifier: {schema!r}"
            raise ValueError(msg)

        if not isinstance(site_id, str) or not _SITE_ID_RE.fullmatch(site_id):
            msg = f"Invalid site_id identifier: {site_id!r}"
            raise ValueError(msg)

        if not values:
            msg = "values sequence must not be empty"
            raise ValueError(msg)

        for val in values:
            if not isinstance(val, str) or not _VALUE_RE.fullmatch(val):
                msg = f"Invalid value identifier: {val!r}"
                raise ValueError(msg)

        path = self._client.build_legacy_v2_global_api_path("/stats/recent/series")
        params: dict[str, Any] = {
            "schema": schema,
            "period": period,
            "end": int_end,
            "filter": f"siteId.eq('{site_id}')",
            "projection": f"values({','.join(values)})",
        }

        response = await self._client._get(
            path,
            params=params,
            expected_unsupported=expected_unsupported,
        )

        if isinstance(response, list):
            raw_items: list[Any] = response
        elif isinstance(response, dict):
            data = response.get("data")
            if isinstance(data, list):
                raw_items = data
            else:
                raise UniFiResponseError(
                    "statistics series response payload is malformed",
                    status_code=200,
                    response_body=None,
                )
        else:
            raise UniFiResponseError(
                "statistics series response payload is malformed",
                status_code=200,
                response_body=None,
            )

        return parse_records(StatsSeries, raw_items, "statistics series")
