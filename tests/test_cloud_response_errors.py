"""Library exceptions for missing and malformed Site Manager, Mobility and InnerSpace reads."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from unittest.mock import AsyncMock

import pytest

from unifi_official_api import ApiKeyAuth, ConnectionType, LocalAuth
from unifi_official_api.exceptions import UniFiNotFoundError, UniFiResponseError
from unifi_official_api.innerspace import UniFiInnerSpaceClient
from unifi_official_api.mobility import UniFiMobilityClient
from unifi_official_api.site_manager import UniFiSiteManagerClient

SECRET = "do-not-leak-7f3a"


def _site_manager() -> UniFiSiteManagerClient:
    return UniFiSiteManagerClient(auth=ApiKeyAuth(api_key="key"), base_url="https://api.ui.com")


def _mobility() -> UniFiMobilityClient:
    return UniFiMobilityClient(auth=ApiKeyAuth(api_key="key"), base_url="https://api.ui.com")


def _innerspace() -> UniFiInnerSpaceClient:
    return UniFiInnerSpaceClient(
        auth=LocalAuth(api_key="key", verify_ssl=False),
        base_url="https://192.168.1.1",
        connection_type=ConnectionType.LOCAL,
    )


# (factory, call, whether the record must carry an id)
_READS: list[tuple[Callable[[], Any], Callable[[Any], Awaitable[Any]], bool]] = [
    (_site_manager, lambda c: c.hosts.get("h-1"), True),
    (_site_manager, lambda c: c.sd_wan.get_config("cfg-1"), True),
    (_site_manager, lambda c: c.sd_wan.get_status("cfg-1"), True),
    (_mobility, lambda c: c.devices.get("ws-1", "d-1"), True),
    (_innerspace, lambda c: c.application.get_info(), False),
]
_IDS = ["hosts.get", "sd_wan.get_config", "sd_wan.get_status", "mobility.get", "innerspace.info"]


@pytest.mark.parametrize("response", [None, {}, {"data": []}, {"data": "x"}, {"data": {}}])
@pytest.mark.parametrize(("factory", "call", "needs_id"), _READS, ids=_IDS)
async def test_read_without_record_raises_not_found(
    factory: Callable[[], Any],
    call: Callable[[Any], Awaitable[Any]],
    needs_id: bool,
    response: Any,
) -> None:
    """A 2xx read whose body holds no record raises UniFiNotFoundError, status 200."""
    del needs_id
    client = factory()
    client._get = AsyncMock(return_value=response)
    with pytest.raises(UniFiNotFoundError) as exc_info:
        await call(client)
    assert exc_info.value.status_code == 200
    client._get.assert_awaited_once()


@pytest.mark.parametrize(
    ("factory", "call"),
    [(f, c) for f, c, needs_id in _READS if needs_id],
    ids=[i for i, r in zip(_IDS, _READS, strict=True) if r[2]],
)
async def test_read_record_without_id_raises_not_found(
    factory: Callable[[], Any], call: Callable[[Any], Awaitable[Any]]
) -> None:
    """A record without an id is no record of an id-keyed resource."""
    client = factory()
    client._get = AsyncMock(return_value={"data": {"name": "x"}})
    with pytest.raises(UniFiNotFoundError):
        await call(client)


@pytest.mark.parametrize(("factory", "call", "needs_id"), _READS, ids=_IDS)
async def test_read_malformed_record_raises_sanitized_response_error(
    factory: Callable[[], Any],
    call: Callable[[Any], Awaitable[Any]],
    needs_id: bool,
) -> None:
    """A malformed record raises UniFiResponseError naming fields, never values."""
    del needs_id
    bad = [{"nested": [SECRET]}]
    client = factory()
    client._get = AsyncMock(
        return_value={
            "data": {
                "id": "x-1",
                "name": bad,
                "hardwareId": bad,
                "type": bad,
                "status": bad,
                "applicationVersion": bad,
                "version": bad,
                "reportedState": bad,
            }
        }
    )
    with pytest.raises(UniFiResponseError) as exc_info:
        await call(client)
    err = exc_info.value
    assert not isinstance(err, UniFiNotFoundError)
    assert err.status_code == 200
    assert SECRET not in err.message
    assert err.__cause__ is None
    assert err.__context__ is None
