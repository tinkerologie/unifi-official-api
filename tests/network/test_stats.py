"""Tests for UniFi Network statistics endpoint and path builders."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from aioresponses import CallbackResult, aioresponses

from unifi_official_api import ApiKeyAuth, ConnectionType, LocalAuth
from unifi_official_api.exceptions import (
    UniFiAuthenticationError,
    UniFiNotFoundError,
    UniFiRateLimitError,
    UniFiResponseError,
    UniFiTimeoutError,
)
from unifi_official_api.network import (
    StatisticsSource,
    StatsSeries,
    StatsSeriesBucket,
    UniFiNetworkClient,
)
from unifi_official_api.network.endpoints import StatsEndpoint
from unifi_official_api.network.models import STATS_PERIODS


class TestStatsPathBuilder:
    """Tests for build_legacy_v2_global_api_path."""

    async def test_build_path_local(self) -> None:
        """Test local path builder pins exact URL, slash normalization, no /site/."""
        async with UniFiNetworkClient(
            auth=LocalAuth(api_key="test-key"),
            base_url="https://192.168.1.1",
            connection_type=ConnectionType.LOCAL,
        ) as client:
            path1 = client.build_legacy_v2_global_api_path("/stats/source")
            assert path1 == "/proxy/network/v2/api/stats/source"
            assert "/site/" not in path1

            path2 = client.build_legacy_v2_global_api_path("stats/recent/series")
            assert path2 == "/proxy/network/v2/api/stats/recent/series"
            assert "/site/" not in path2

    async def test_build_path_remote(self) -> None:
        """Test remote path builder pins exact connector URL without /proxy."""
        async with UniFiNetworkClient(
            auth=ApiKeyAuth(api_key="test-key"),
            connection_type=ConnectionType.REMOTE,
            console_id="cid-12345",
        ) as client:
            path = client.build_legacy_v2_global_api_path("/stats/recent/series")
            expected = "/v1/connector/consoles/cid-12345/network/v2/api/stats/recent/series"
            assert path == expected
            assert "/proxy" not in path
            assert "/site/" not in path

    async def test_build_path_remote_requires_console_id(self) -> None:
        """Test remote path builder raises ValueError when console_id is missing."""
        async with UniFiNetworkClient(
            auth=ApiKeyAuth(api_key="test-key"),
            connection_type=ConnectionType.REMOTE,
            console_id=None,
        ) as client:
            with pytest.raises(ValueError, match="console_id is required"):
                client.build_legacy_v2_global_api_path("/stats/source")


class TestStatsEndpoint:
    """Tests for StatsEndpoint functionality."""

    async def test_client_stats_accessor_and_exports(self) -> None:
        """Test client.stats property accessor and public exports."""
        async with UniFiNetworkClient(
            auth=LocalAuth(api_key="test-key"),
            base_url="https://192.168.1.1",
            connection_type=ConnectionType.LOCAL,
        ) as client:
            assert isinstance(client.stats, StatsEndpoint)

        assert StatsEndpoint is not None
        assert StatisticsSource is not None
        assert StatsSeries is not None
        assert StatsSeriesBucket is not None
        assert {"HOUR", "DAY", "WEEK", "MONTH"} == STATS_PERIODS

    async def test_get_source_local_and_remote(
        self,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test get_source for local and remote connections with bare strings."""
        # Local
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/v2/api/stats/source",
            payload="MODERN",
        )
        async with UniFiNetworkClient(
            auth=LocalAuth(api_key="test-key"),
            base_url="https://192.168.1.1",
            connection_type=ConnectionType.LOCAL,
        ) as client:
            source = await client.stats.get_source()
            assert isinstance(source, StatisticsSource)
            assert source.root == "MODERN"

        # Remote
        mock_aioresponse.get(
            "https://api.ui.com/v1/connector/consoles/cid-123/network/v2/api/stats/source",
            payload="LEGACY",
        )
        async with UniFiNetworkClient(
            auth=ApiKeyAuth(api_key="test-key"),
            connection_type=ConnectionType.REMOTE,
            console_id="cid-123",
        ) as client:
            source2 = await client.stats.get_source()
            assert source2.root == "LEGACY"

    async def test_get_source_invalid_payload(
        self,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test get_source raises sanitized UniFiResponseError on unknown payload."""
        mock_aioresponse.get(
            "https://192.168.1.1/proxy/network/v2/api/stats/source",
            payload="UNKNOWN_SOURCE_LABEL",
        )
        async with UniFiNetworkClient(
            auth=LocalAuth(api_key="test-key"),
            base_url="https://192.168.1.1",
            connection_type=ConnectionType.LOCAL,
        ) as client:
            with pytest.raises(UniFiResponseError) as exc_info:
                await client.stats.get_source()
            assert exc_info.value.status_code == 200
            assert "UNKNOWN_SOURCE_LABEL" not in str(exc_info.value)

    async def test_get_recent_series_query_parameters(
        self,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test get_recent_series pins exact query params and excludes start."""
        recorded_url: str | None = None

        def callback(url: Any, **kwargs: Any) -> Any:
            nonlocal recorded_url
            recorded_url = str(url)
            return CallbackResult(payload=[])

        mock_aioresponse.get(
            re.compile(r"^https://192.168.1.1/proxy/network/v2/api/stats/recent/series.*"),
            callback=callback,
        )

        async with UniFiNetworkClient(
            auth=LocalAuth(api_key="test-key"),
            base_url="https://192.168.1.1",
            connection_type=ConnectionType.LOCAL,
        ) as client:
            series = await client.stats.get_recent_series(
                schema="wanBySite",
                site_id="ab632056-1234-5678-9abc-def012345678",
                period="DAY",
                end_ms=1700000000000,
                values=("rxBytes", "txBytes"),
            )
            assert series == []

        assert recorded_url is not None
        parsed = urlparse(recorded_url)
        params = parse_qs(parsed.query)

        assert params["schema"] == ["wanBySite"]
        assert params["period"] == ["DAY"]
        assert params["end"] == ["1700000000000"]
        assert params["filter"] == ["siteId.eq('ab632056-1234-5678-9abc-def012345678')"]
        assert params["projection"] == ["values(rxBytes,txBytes)"]
        assert "start" not in params

    @pytest.mark.parametrize("period", ["HOUR", "DAY", "WEEK", "MONTH"])
    async def test_get_recent_series_all_periods(
        self,
        period: Any,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test all four valid periods are accepted."""
        mock_aioresponse.get(
            re.compile(r"^https://192.168.1.1/proxy/network/v2/api/stats/recent/series.*"),
            payload=[],
        )
        async with UniFiNetworkClient(
            auth=LocalAuth(api_key="test-key"),
            base_url="https://192.168.1.1",
            connection_type=ConnectionType.LOCAL,
        ) as client:
            res = await client.stats.get_recent_series(
                schema="wanBySite",
                site_id="site-1",
                period=period,
                end_ms=1600000000000,
            )
            assert res == []

    async def test_get_recent_series_parses_remote_buckets(
        self,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Check the remote path, exact parameters, and partial bucket data."""
        recorded_url = None

        def callback(url: Any, **kwargs: Any) -> CallbackResult:
            nonlocal recorded_url
            recorded_url = url
            return CallbackResult(
                payload=[
                    {
                        "siteId": "site-1",
                        "series": [
                            {
                                "timestamp": 0,
                                "duration": 137,
                                "rxBytes": 0,
                                "txBytes": 12.5,
                                "durationMs": 137,
                            }
                        ],
                    }
                ]
            )

        mock_aioresponse.get(
            re.compile(
                r"^https://api\.ui\.com/v1/connector/consoles/test-console/network/"
                r"v2/api/stats/recent/series\?"
            ),
            callback=callback,
        )
        async with UniFiNetworkClient(
            auth=ApiKeyAuth(api_key="test-key"),
            connection_type=ConnectionType.REMOTE,
            console_id="test-console",
        ) as client:
            (site,) = await client.stats.get_recent_series(
                schema="wanBySite",
                site_id="site-1",
                period="MONTH",
                end_ms=0,
                values=["txBytes", "rxBytes"],
            )

        assert recorded_url is not None
        assert parse_qs(urlparse(str(recorded_url)).query) == {
            "schema": ["wanBySite"],
            "period": ["MONTH"],
            "end": ["0"],
            "filter": ["siteId.eq('site-1')"],
            "projection": ["values(txBytes,rxBytes)"],
        }
        assert site.site_id == "site-1"
        (bucket,) = site.series
        assert (bucket.timestamp, bucket.duration, bucket.rx_bytes, bucket.tx_bytes) == (
            0,
            137,
            0.0,
            12.5,
        )
        assert bucket.model_extra == {"durationMs": 137}

    @pytest.mark.parametrize(
        ("argument", "value"),
        [
            ("period", "INVALID"),
            ("period", []),
            ("end_ms", True),
            ("end_ms", "bad"),
            ("end_ms", -100),
            ("end_ms", 1000.0),
            ("schema", ""),
            ("schema", "schema'quote"),
            ("schema", "wanBySite\n"),
            ("schema", "1schema"),
            ("schema", "a" * 65),
            ("schema", 1),
            ("site_id", ""),
            ("site_id", "site'id"),
            ("site_id", "site-1\n"),
            ("site_id", "site_1"),
            ("site_id", "a" * 65),
            ("site_id", 1),
            ("values", ()),
            ("values", "rxBytes"),
            ("values", b"rxBytes"),
            ("values", {"rxBytes"}),
            ("values", ("rxBytes", "rxBytes")),
            ("values", ("rxBytes", "bad'val")),
            ("values", ("rxBytes", "rxBytes\n")),
            ("values", ("rxBytes", 1)),
        ],
    )
    async def test_validation_before_io(
        self, argument: str, value: object, mock_aioresponse: aioresponses
    ) -> None:
        """Reject malformed arguments before constructing a request."""
        params: dict[str, Any] = {
            "schema": "wanBySite",
            "site_id": "site-1",
            "period": "DAY",
            "end_ms": 1000,
        }
        params[argument] = value
        async with UniFiNetworkClient(
            auth=LocalAuth(api_key="test-key"),
            base_url="https://192.168.1.1",
            connection_type=ConnectionType.LOCAL,
        ) as client:
            with pytest.raises(ValueError):
                await client.stats.get_recent_series(**params)
        assert not mock_aioresponse.requests

    async def test_malformed_response_shapes(
        self,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test malformed response shapes raise sanitized UniFiResponseError."""
        async with UniFiNetworkClient(
            auth=LocalAuth(api_key="test-key"),
            base_url="https://192.168.1.1",
            connection_type=ConnectionType.LOCAL,
        ) as client:
            # 1. A data envelope
            mock_aioresponse.get(
                re.compile(r"^https://192.168.1.1/proxy/network/v2/api/stats/recent/series.*"),
                payload={"data": []},
            )
            with pytest.raises(UniFiResponseError) as exc1:
                await client.stats.get_recent_series(
                    schema="wanBySite",
                    site_id="site-1",
                    period="DAY",
                    end_ms=1000,
                )
            assert exc1.value.status_code == 200
            assert exc1.value.response_body is None
            assert exc1.value.__cause__ is None
            assert exc1.value.__context__ is None

            # 2. Unexpected top-level object
            mock_aioresponse.get(
                re.compile(r"^https://192.168.1.1/proxy/network/v2/api/stats/recent/series.*"),
                payload={"unexpected": True},
            )
            with pytest.raises(UniFiResponseError):
                await client.stats.get_recent_series(
                    schema="wanBySite",
                    site_id="site-1",
                    period="DAY",
                    end_ms=1000,
                )

            # 3. Malformed structural record
            mock_aioresponse.get(
                re.compile(r"^https://192.168.1.1/proxy/network/v2/api/stats/recent/series.*"),
                payload=[{"siteId": "site-1", "series": "not-a-list-of-buckets"}],
            )
            with pytest.raises(UniFiResponseError):
                await client.stats.get_recent_series(
                    schema="wanBySite",
                    site_id="site-1",
                    period="DAY",
                    end_ms=1000,
                )

            # 4. Non-dict non-list top level (e.g. string or integer)
            mock_aioresponse.get(
                re.compile(r"^https://192.168.1.1/proxy/network/v2/api/stats/recent/series.*"),
                payload="bare-string",
            )
            with pytest.raises(UniFiResponseError):
                await client.stats.get_recent_series(
                    schema="wanBySite",
                    site_id="site-1",
                    period="DAY",
                    end_ms=1000,
                )

    async def test_error_sanitization_excludes_secrets(
        self,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test validation errors sanitize output and exclude secret input sentinels."""
        secret_sentinel = "SUPER_SECRET_PAYLOAD_TOKEN_12345"
        mock_aioresponse.get(
            re.compile(r"^https://192.168.1.1/proxy/network/v2/api/stats/recent/series.*"),
            payload=[{"siteId": secret_sentinel, "series": [{"timestamp": "bad"}]}],
        )
        async with UniFiNetworkClient(
            auth=LocalAuth(api_key="test-key"),
            base_url="https://192.168.1.1",
            connection_type=ConnectionType.LOCAL,
        ) as client:
            with pytest.raises(UniFiResponseError) as exc_info:
                await client.stats.get_recent_series(
                    schema="wanBySite",
                    site_id="site-1",
                    period="DAY",
                    end_ms=1000,
                )
            err = exc_info.value
            assert secret_sentinel not in str(err)
            assert secret_sentinel not in str(err.args)
            assert err.__cause__ is None
            assert err.__context__ is None
            assert err.response_body is None

    async def test_http_error_translation(
        self,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test HTTP 401, 403, 404, 429, 500, non-JSON 2xx, and timeout mapping."""
        pattern = re.compile(r"^https://192.168.1.1/proxy/network/v2/api/stats/.*")

        async with UniFiNetworkClient(
            auth=LocalAuth(api_key="test-key"),
            base_url="https://192.168.1.1",
            connection_type=ConnectionType.LOCAL,
        ) as client:
            # 401
            mock_aioresponse.get(pattern, status=401)
            with pytest.raises(UniFiAuthenticationError):
                await client.stats.get_source()

            # 403
            mock_aioresponse.get(pattern, status=403)
            with pytest.raises(UniFiAuthenticationError):
                await client.stats.get_recent_series(
                    schema="wanBySite", site_id="site-1", period="DAY", end_ms=1000
                )

            # 404
            mock_aioresponse.get(pattern, status=404)
            with pytest.raises(UniFiNotFoundError):
                await client.stats.get_source()

            # 429
            mock_aioresponse.get(pattern, status=429, headers={"Retry-After": "5"})
            with pytest.raises(UniFiRateLimitError) as exc_429:
                await client.stats.get_source()
            assert exc_429.value.retry_after == 5

            # 500
            mock_aioresponse.get(pattern, status=500, body="Internal error")
            with pytest.raises(UniFiResponseError):
                await client.stats.get_source()

            # non-JSON 2xx
            mock_aioresponse.get(pattern, status=200, body="NON_JSON_HTML")
            with pytest.raises(UniFiResponseError) as exc_non_json:
                await client.stats.get_source()
            assert "non-JSON" in exc_non_json.value.message

            # Timeout
            mock_aioresponse.get(pattern, exception=TimeoutError())
            with pytest.raises(UniFiTimeoutError):
                await client.stats.get_source()
