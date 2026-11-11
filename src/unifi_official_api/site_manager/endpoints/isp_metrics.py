"""ISP Metrics endpoint for UniFi Site Manager API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...exceptions import UniFiValidationError
from ...validation import parse_record, parse_records
from ..models.isp_metric import ISPMetric, ISPMetricQuery, ISPMetricQueryResult

if TYPE_CHECKING:
    from datetime import datetime

    from ..client import UniFiSiteManagerClient


class ISPMetricsEndpoint:
    """Endpoint for retrieving and querying ISP WAN performance metrics."""

    def __init__(self, client: UniFiSiteManagerClient) -> None:
        """
        Initialize the ISP metrics endpoint.

        Args:
            client: The UniFi Site Manager client.
        """
        self._client = client

    async def get_metrics(
        self,
        metric_type: str,
        *,
        host_id: str | None = None,
        duration: str | None = None,
        begin_timestamp: datetime | None = None,
        end_timestamp: datetime | None = None,
    ) -> list[ISPMetric]:
        """
        Return ISP metrics by host and site without pagination.

        Args:
            metric_type: Aggregation interval (``5m`` or ``1h``).
            host_id: Legacy filter. The published API has no ``hostId`` parameter.
            duration: ``24h`` for ``5m``, or ``7d`` or ``30d`` for ``1h``.
                The API accepts a duration or timestamps.
            begin_timestamp: Optional timezone-aware start time.
            end_timestamp: Optional timezone-aware end time.

        Returns:
            List of host and site records with timestamped periods.

        Raises:
            UniFiResponseError: If an item in the response fails validation.
        """
        path = self._client._isp_metrics_path(metric_type)
        params = self._client._isp_metrics_params(
            begin_timestamp, end_timestamp, duration or None, host_id=host_id
        )
        response = await self._client._get(path, params=params)
        data = self._client._response_data(response, fallback=response)
        if isinstance(data, list):
            return parse_records(ISPMetric, data, "ISP metric")
        return []

    async def query(
        self,
        metric_type: str,
        query_data: ISPMetricQuery | dict[str, Any],
    ) -> ISPMetricQueryResult:
        """
        Query historical ISP metrics for specific sites without pagination.

        Args:
            metric_type: Aggregation interval (``5m`` or ``1h``).
            query_data: A query with ``sites`` or a dictionary payload.
                Legacy typed queries keep their original serialization.

        Returns:
            ISPMetricQueryResult containing matching metrics.

        Raises:
            UniFiValidationError: If a typed query combines ``sites`` and legacy fields.
            UniFiResponseError: If the query result in the response fails validation.
        """
        path = self._client._isp_metrics_query_path(metric_type)
        response = await self._client._post(path, json_data=self._query_payload(query_data))
        data = self._client._response_data(response, fallback=response)
        if isinstance(data, dict):
            return parse_record(ISPMetricQueryResult, data, "ISP metric query")
        return ISPMetricQueryResult()

    def _query_payload(self, query_data: ISPMetricQuery | dict[str, Any]) -> dict[str, Any]:
        if isinstance(query_data, dict):
            return query_data
        if query_data.sites is None:
            return query_data.model_dump(by_alias=True, exclude_none=True)

        legacy_fields = {"host_ids", "time_range_start", "time_range_end"}
        if query_data.host_ids or legacy_fields & query_data.model_fields_set:
            msg = "ISP metrics queries cannot combine sites with legacy fields"
            raise UniFiValidationError(msg)

        sites = [
            site.model_dump(
                by_alias=True, exclude_none=True, exclude={"begin_timestamp", "end_timestamp"}
            )
            | self._client._isp_metrics_timestamps(site.begin_timestamp, site.end_timestamp)
            for site in query_data.sites
        ]
        return self._client._isp_metrics_query_body(sites)
