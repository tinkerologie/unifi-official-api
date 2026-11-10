"""Statistics endpoint for UniFi Network API."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal

from ...exceptions import UniFiResponseError
from ...validation import parse_record, parse_records
from ..models.stats import STATS_PERIODS, StatisticsSource, StatsSeries

if TYPE_CHECKING:
    from ..client import UniFiNetworkClient

DEFAULT_STATS_VALUES: tuple[str, ...] = ("rxBytes", "txBytes")

_IDENTIFIER_RE = re.compile(r"[A-Za-z][A-Za-z0-9]{0,63}")
_SITE_ID_RE = re.compile(r"[0-9A-Za-z-]{1,64}")


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

    async def get_source(self) -> StatisticsSource:
        """
        Query the active statistics engine source mode.

        This controller-wide endpoint is outside the Integration API. A
        site-scoped request returns HTTP 404. Network 10 reports LEGACY and
        Network 11 reports MODERN. Use an admin API key. View-Only keys
        receive HTTP 403. The remote path was verified on Network 11.1.47.

        Returns:
            StatisticsSource indicating "LEGACY" or "MODERN".

        Raises:
            UniFiAuthenticationError: If authentication fails.
            UniFiResponseError: If the controller returns an unexpected payload.

        """
        path = self._client.build_legacy_v2_global_api_path("/stats/source")
        response = await self._client._get(
            path,
            expected_unsupported=True,
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
    ) -> list[StatsSeries]:
        """
        Fetch recent statistics series for a schema and site.

        HOUR and DAY return 5-minute buckets, WEEK returns hourly buckets,
        and MONTH returns 8-hour buckets across up to 30 days. The newest
        bucket can be partial. Byte totals are additive across buckets.
        This method sends period and end because support for start began
        with Network 11.0.89. The local path is covered by mock tests.

        Args:
            schema: The statistics schema name (e.g. "wanBySite").
            site_id: The Classic site `_id` from `sites.get_legacy_all()`. The
                Integration API site ID maps to the Classic `external_id`.
            period: Aggregation window period ("HOUR", "DAY",
                "WEEK", or "MONTH").
            end_ms: End timestamp in milliseconds since epoch.
            values: Attribute field names to project (defaults to
                ("rxBytes", "txBytes")).

        Returns:
            List of validated StatsSeries instances.

        Raises:
            ValueError: If parameters fail validation before request.
            UniFiAuthenticationError: If authentication fails, including HTTP 403
                for a View-Only key.
            UniFiResponseError: If the controller returns a malformed response.

        """
        if not isinstance(period, str) or period not in STATS_PERIODS:
            msg = f"Unsupported period; expected one of {sorted(STATS_PERIODS)}"
            raise ValueError(msg)
        if type(end_ms) is not int or end_ms < 0:
            msg = "end_ms must be a nonnegative integer millisecond timestamp"
            raise ValueError(msg)
        if not isinstance(schema, str) or not _IDENTIFIER_RE.fullmatch(schema):
            msg = "Invalid schema identifier"
            raise ValueError(msg)
        if not isinstance(site_id, str) or not _SITE_ID_RE.fullmatch(site_id):
            msg = "Invalid site_id identifier"
            raise ValueError(msg)
        if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
            msg = "values must be a sequence of identifiers"
            raise ValueError(msg)
        if not values:
            msg = "values sequence must not be empty"
            raise ValueError(msg)
        if any(
            not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value) for value in values
        ):
            msg = "Invalid value identifier"
            raise ValueError(msg)
        if len(set(values)) != len(values):
            msg = "values must contain unique identifiers"
            raise ValueError(msg)

        path = self._client.build_legacy_v2_global_api_path("/stats/recent/series")
        params: dict[str, str] = {
            "schema": schema,
            "period": period,
            "end": str(end_ms),
            "filter": f"siteId.eq('{site_id}')",
            "projection": f"values({','.join(values)})",
        }

        response = await self._client._get(
            path,
            params=params,
            expected_unsupported=True,
        )

        if not isinstance(response, list):
            raise UniFiResponseError(
                "statistics series response payload is malformed",
                status_code=200,
            )
        return parse_records(StatsSeries, response, "statistics series")
