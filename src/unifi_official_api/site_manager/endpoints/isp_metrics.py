"""ISP Metrics endpoint for UniFi Site Manager API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..models.isp_metric import ISPMetric, ISPMetricQuery, ISPMetricQueryResult

if TYPE_CHECKING:
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
    ) -> list[ISPMetric]:
        """
        Get ISP metrics for a specific type.

        Args:
            metric_type: Metric type (e.g. latency, throughput, uptime).
            host_id: Optional host filter.
            duration: Optional duration string (e.g. 24h, 7d).

        Returns:
            List of ISPMetric data points.
        """
        params: dict[str, Any] = {}
        if host_id:
            params["hostId"] = host_id
        if duration:
            params["duration"] = duration
        response = await self._client._get(
            f"/v1/isp-metrics/{metric_type}", params=params if params else None
        )
        if response is None:
            return []
        data = response.get("data", response) if isinstance(response, dict) else response
        if isinstance(data, list):
            return [ISPMetric.model_validate(item) for item in data]
        return []

    async def query(
        self,
        metric_type: str,
        query_data: ISPMetricQuery | dict[str, Any],
    ) -> ISPMetricQueryResult:
        """
        Query historical ISP metrics across multiple hosts and time intervals.

        Args:
            metric_type: Metric type (e.g. latency, packet-loss).
            query_data: Query parameters.

        Returns:
            ISPMetricQueryResult containing matching metrics.
        """
        payload = (
            query_data.model_dump(by_alias=True, exclude_none=True)
            if isinstance(query_data, ISPMetricQuery)
            else query_data
        )
        response = await self._client._post(
            f"/v1/isp-metrics/{metric_type}/query", json_data=payload
        )
        if isinstance(response, dict):
            data = response.get("data", response)
            if isinstance(data, dict):
                return ISPMetricQueryResult.model_validate(data)
        return ISPMetricQueryResult()
