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
            return CallbackResult(payload={"data": []})

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

    async def test_get_recent_series_enveloped_and_raw_responses(
        self,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test parsing both raw series list and {data: [...]} envelope."""
        sample_record = {
            "siteId": "ab632056-1234-5678-9abc-def012345678",
            "series": [
                {
                    "timestamp": 1600000000000,
                    "duration": 300000,
                    "rxBytes": 1048576.0,
                    "txBytes": 524288.0,
                }
            ],
        }

        # 1. Enveloped data
        mock_aioresponse.get(
            re.compile(r"^https://192.168.1.1/proxy/network/v2/api/stats/recent/series.*"),
            payload={"data": [sample_record]},
        )
        async with UniFiNetworkClient(
            auth=LocalAuth(api_key="test-key"),
            base_url="https://192.168.1.1",
            connection_type=ConnectionType.LOCAL,
        ) as client:
            res1 = await client.stats.get_recent_series(
                schema="wanBySite",
                site_id="ab632056-1234-5678-9abc-def012345678",
                period="DAY",
                end_ms=1600000000000,
            )
            assert len(res1) == 1
            assert res1[0].site_id == "ab632056-1234-5678-9abc-def012345678"
            assert len(res1[0].series) == 1
            assert res1[0].series[0].rx_bytes == 1048576.0

        # 2. Raw list
        mock_aioresponse.get(
            re.compile(r"^https://192.168.1.1/proxy/network/v2/api/stats/recent/series.*"),
            payload=[sample_record],
        )
        async with UniFiNetworkClient(
            auth=LocalAuth(api_key="test-key"),
            base_url="https://192.168.1.1",
            connection_type=ConnectionType.LOCAL,
        ) as client:
            res2 = await client.stats.get_recent_series(
                schema="wanBySite",
                site_id="ab632056-1234-5678-9abc-def012345678",
                period="DAY",
                end_ms=1600000000000,
            )
            assert len(res2) == 1

    async def test_validation_before_io(self) -> None:
        """Test parameter validation fails before any I/O is performed."""
        async with UniFiNetworkClient(
            auth=LocalAuth(api_key="test-key"),
            base_url="https://192.168.1.1",
            connection_type=ConnectionType.LOCAL,
        ) as client:
            # Bad period
            with pytest.raises(ValueError, match="Unsupported period"):
                await client.stats.get_recent_series(
                    schema="wanBySite",
                    site_id="site-1",
                    period="INVALID",  # type: ignore[arg-type]
                    end_ms=1000,
                )

            # Bad end_ms (bool, string, negative, nonfinite)
            for bad_end in [True, False, "bad", -100, float("inf"), float("nan"), 1000.75]:
                with pytest.raises(ValueError, match="end_ms must be"):
                    await client.stats.get_recent_series(
                        schema="wanBySite",
                        site_id="site-1",
                        period="DAY",
                        end_ms=bad_end,  # type: ignore[arg-type]
                    )

            # Bad schema
            for bad_schema in [
                "",
                "schema;drop",
                "schema with space",
                "schema'quote",
                "wanBySite\n",
            ]:
                with pytest.raises(ValueError, match="Invalid schema identifier"):
                    await client.stats.get_recent_series(
                        schema=bad_schema,
                        site_id="site-1",
                        period="DAY",
                        end_ms=1000,
                    )

            # Bad site_id (filter injection prevention)
            for bad_site in ["", "site'id", "site;inject", "site with spaces", "site-1\n"]:
                with pytest.raises(ValueError, match="Invalid site_id identifier"):
                    await client.stats.get_recent_series(
                        schema="wanBySite",
                        site_id=bad_site,
                        period="DAY",
                        end_ms=1000,
                    )

            # Empty values
            with pytest.raises(ValueError, match="values sequence must not be empty"):
                await client.stats.get_recent_series(
                    schema="wanBySite",
                    site_id="site-1",
                    period="DAY",
                    end_ms=1000,
                    values=(),
                )

            # Bad value identifiers
            for bad_val in ["", "bad;val", "bad'val", "bad val", "rxBytes\n"]:
                with pytest.raises(ValueError, match="Invalid value identifier"):
                    await client.stats.get_recent_series(
                        schema="wanBySite",
                        site_id="site-1",
                        period="DAY",
                        end_ms=1000,
                        values=("rxBytes", bad_val),
                    )

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
            # 1. Non-list data in dict
            mock_aioresponse.get(
                re.compile(r"^https://192.168.1.1/proxy/network/v2/api/stats/recent/series.*"),
                payload={"data": "not-a-list"},
            )
            with pytest.raises(UniFiResponseError) as exc1:
                await client.stats.get_recent_series(
                    schema="wanBySite",
                    site_id="site-1",
                    period="DAY",
                    end_ms=1000,
                )
            assert exc1.value.status_code == 200

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

    async def test_oversized_timestamp_is_a_sanitized_response_error(
        self,
        mock_aioresponse: aioresponses,
    ) -> None:
        """Test an integer timestamp too large for a float raises the package error."""
        mock_aioresponse.get(
            re.compile(r"^https://192.168.1.1/proxy/network/v2/api/stats/recent/series.*"),
            body='[{"siteId": "site-1", "series": [{"timestamp": 1'
            + "0" * 400
            + ', "duration": 300000}]}]',
            content_type="application/json",
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
            assert exc_info.value.status_code == 200
            assert exc_info.value.response_body is None

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
                await client.stats.get_source(expected_unsupported=False)
            assert "non-JSON" in exc_non_json.value.message

            # Timeout
            mock_aioresponse.get(pattern, exception=TimeoutError())
            with pytest.raises(UniFiTimeoutError):
                await client.stats.get_source()
