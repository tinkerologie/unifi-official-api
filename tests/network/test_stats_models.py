"""Tests for UniFi Network statistics models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from unifi_official_api.network.models.stats import (
    StatisticsSource,
    StatsSeries,
    StatsSeriesBucket,
)


class TestStatisticsSource:
    """Tests for StatisticsSource model."""

    def test_valid_sources(self) -> None:
        """Test valid legacy and modern sources."""
        modern = StatisticsSource.model_validate("MODERN")
        assert modern.root == "MODERN"

        legacy = StatisticsSource.model_validate("LEGACY")
        assert legacy.root == "LEGACY"

    def test_invalid_sources(self) -> None:
        """Test unknown source labels and malformed payloads are rejected."""
        for invalid in ["UNKNOWN", "OTHER", "modern", "", 123, None, {}]:
            with pytest.raises(ValidationError):
                StatisticsSource.model_validate(invalid)


class TestStatsSeriesBucket:
    """Tests for StatsSeriesBucket model."""

    def test_valid_bucket_camel_case(self) -> None:
        """Test valid bucket with camelCase aliases."""
        bucket = StatsSeriesBucket.model_validate(
            {
                "timestamp": 1600000000000,
                "duration": 300000,
                "rxBytes": 1048576.5,
                "txBytes": 524288.25,
            }
        )
        assert bucket.timestamp == 1600000000000
        assert bucket.duration == 300000
        assert bucket.rx_bytes == 1048576.5
        assert bucket.tx_bytes == 524288.25

    def test_valid_bucket_snake_case(self) -> None:
        """Test valid bucket with snake_case fields via populate_by_name."""
        bucket = StatsSeriesBucket.model_validate(
            {
                "timestamp": 1600000000000,
                "duration": 300000,
                "rx_bytes": 1048576.0,
                "tx_bytes": 524288.0,
            }
        )
        assert bucket.rx_bytes == 1048576.0
        assert bucket.tx_bytes == 524288.0

    def test_partial_duration(self) -> None:
        """Test bucket with partial duration (e.g. current incomplete interval)."""
        bucket = StatsSeriesBucket.model_validate(
            {
                "timestamp": 1600000000000,
                "duration": 270216,
            }
        )
        assert bucket.duration == 270216
        assert bucket.rx_bytes is None
        assert bucket.tx_bytes is None

    def test_zero_and_fractional_bytes_preserved(self) -> None:
        """Test legitimate zero and fractional byte values are preserved."""
        bucket = StatsSeriesBucket.model_validate(
            {
                "timestamp": 1600000000000,
                "duration": 300000,
                "rxBytes": 0,
                "txBytes": 0.0,
            }
        )
        assert bucket.rx_bytes == 0.0
        assert bucket.tx_bytes == 0.0

        bucket2 = StatsSeriesBucket.model_validate(
            {
                "timestamp": 1600000000000,
                "duration": 300000,
                "rxBytes": 12.3456,
            }
        )
        assert bucket2.rx_bytes == 12.3456
        assert bucket2.tx_bytes is None

    def test_invalid_and_negative_bytes_coerced_to_none(self) -> None:
        """Test missing/nonfinite/negative/bool byte fields are treated as absent."""
        bucket = StatsSeriesBucket.model_validate(
            {
                "timestamp": 1600000000000,
                "duration": 300000,
                "rxBytes": -1,
                "txBytes": -50.5,
            }
        )
        assert bucket.rx_bytes is None
        assert bucket.tx_bytes is None

        bucket2 = StatsSeriesBucket.model_validate(
            {
                "timestamp": 1600000000000,
                "duration": 300000,
                "rxBytes": True,
                "txBytes": False,
            }
        )
        assert bucket2.rx_bytes is None
        assert bucket2.tx_bytes is None

        bucket3 = StatsSeriesBucket.model_validate(
            {
                "timestamp": 1600000000000,
                "duration": 300000,
                "rxBytes": float("inf"),
                "txBytes": float("nan"),
            }
        )
        assert bucket3.rx_bytes is None
        assert bucket3.tx_bytes is None

        bucket4 = StatsSeriesBucket.model_validate(
            {
                "timestamp": 1600000000000,
                "duration": 300000,
                "rxBytes": "not-a-number",
                "txBytes": None,
            }
        )
        assert bucket4.rx_bytes is None
        assert bucket4.tx_bytes is None

        # An integer too large for a float is absent, not an OverflowError.
        bucket5 = StatsSeriesBucket.model_validate(
            {"timestamp": 1600000000000, "duration": 300000, "rxBytes": 10**400, "txBytes": 0}
        )
        assert bucket5.rx_bytes is None
        assert bucket5.tx_bytes == 0.0

    def test_timestamp_validation(self) -> None:
        """Test timestamp validation rejects bool, non-numeric, and nonfinite."""
        for bad_ts in [True, False, "bad", float("inf"), float("nan"), None, 10**400]:
            with pytest.raises(ValidationError):
                StatsSeriesBucket.model_validate({"timestamp": bad_ts, "duration": 300000})

    def test_duration_validation(self) -> None:
        """Test duration validation rejects bool, non-positive, and nonfinite."""
        for bad_dur in [
            True,
            False,
            0,
            -1,
            -300000,
            "bad",
            float("inf"),
            float("nan"),
            None,
            10**400,
        ]:
            with pytest.raises(ValidationError):
                StatsSeriesBucket.model_validate({"timestamp": 1600000000000, "duration": bad_dur})

    def test_forward_field_compatibility(self) -> None:
        """Test unknown forward fields are preserved."""
        bucket = StatsSeriesBucket.model_validate(
            {
                "timestamp": 1600000000000,
                "duration": 300000,
                "extraField": "preserved",
                "byNetworkGroup": {"lan": 123},
            }
        )
        assert bucket.extraField == "preserved"  # type: ignore[attr-defined]


class TestStatsSeries:
    """Tests for StatsSeries model."""

    def test_valid_series_camel_case(self) -> None:
        """Test valid series with camelCase siteId alias."""
        data = {
            "siteId": "ab632056-1234-5678-9abc-def012345678",
            "series": [
                {
                    "timestamp": 1600000000000,
                    "duration": 300000,
                    "rxBytes": 100.0,
                    "txBytes": 200.0,
                }
            ],
        }
        series_obj = StatsSeries.model_validate(data)
        assert series_obj.site_id == "ab632056-1234-5678-9abc-def012345678"
        assert len(series_obj.series) == 1
        assert series_obj.series[0].timestamp == 1600000000000

    def test_valid_series_snake_case(self) -> None:
        """Test valid series with site_id field name."""
        series_obj = StatsSeries.model_validate(
            {
                "site_id": "default",
                "series": [],
            }
        )
        assert series_obj.site_id == "default"
        assert series_obj.series == []

    def test_missing_series_rejected(self) -> None:
        """Test that missing series field is rejected rather than defaulted to empty list."""
        with pytest.raises(ValidationError):
            StatsSeries.model_validate({"siteId": "default"})

    def test_invalid_site_id_rejected(self) -> None:
        """Test that empty, whitespace, or non-string siteId is rejected."""
        for bad_site in ["", "   ", 123, None]:
            with pytest.raises(ValidationError):
                StatsSeries.model_validate({"siteId": bad_site, "series": []})

    def test_forward_field_compatibility(self) -> None:
        """Test forward compatibility on series container."""
        series_obj = StatsSeries.model_validate(
            {
                "siteId": "default",
                "series": [],
                "networkVersion": "11.1.47",
            }
        )
        assert series_obj.networkVersion == "11.1.47"  # type: ignore[attr-defined]
