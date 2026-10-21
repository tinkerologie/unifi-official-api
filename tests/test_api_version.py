# Copyright 2026 UniFi Insights contributors
"""Tests for the UniFi Official API version and pinned specification versions."""

from unifi_official_api._version import __version__ as version_from_module
from unifi_official_api.const import (
    ACCESS_DOC_VERSION,
    CARRIER_FABRIC_SPEC_VERSION,
    INNERSPACE_SPEC_VERSION,
    MOBILITY_SPEC_VERSION,
    NETWORK_SPEC_VERSION,
    PROTECT_SPEC_VERSION,
    SITE_MANAGER_SPEC_VERSION,
    USER_AGENT,
    __version__,
)


def test_api_version_drives_user_agent() -> None:
    """Test the public version in _version.py remains the user-agent source."""
    assert version_from_module == "2.0.0"
    assert __version__ == "2.0.0"
    assert f"unifi-official-api/{__version__}" == USER_AGENT


def test_pinned_spec_versions() -> None:
    """Test pinned specification version constants match the verified upstream specs."""
    assert NETWORK_SPEC_VERSION == "10.6.106"
    assert PROTECT_SPEC_VERSION == "7.3.70"
    assert INNERSPACE_SPEC_VERSION == "1.3.23"
    assert MOBILITY_SPEC_VERSION == "1.0.0"
    assert SITE_MANAGER_SPEC_VERSION == "1.0.0"
    assert CARRIER_FABRIC_SPEC_VERSION == "1.0.0"
    assert ACCESS_DOC_VERSION == "2.2.10"
