"""Per-request outcomes for best-effort Protect listings."""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any
from unittest.mock import AsyncMock

import aiohttp
import pytest
from aioresponses import aioresponses

from unifi_official_api import ApiKeyAuth
from unifi_official_api.exceptions import (
    UniFiAuthenticationError,
    UniFiConnectionError,
    UniFiNotFoundError,
    UniFiRateLimitError,
    UniFiResponseError,
    UniFiTimeoutError,
)
from unifi_official_api.protect import ProtectListResult, UniFiProtectClient

FAMILIES = (
    "alarm_hubs",
    "arm_profiles",
    "bridges",
    "cameras",
    "chimes",
    "external_arm_profiles",
    "fobs",
    "lights",
    "link_stations",
    "relays",
    "sensors",
    "sirens",
    "speakers",
    "ulp_users",
    "users",
    "viewers",
)
VALID = {
    "id": "valid",
    "mac": "AA:BB:CC:DD:EE:FF",
    "name": "Example",
    "state": "CONNECTED",
    "firstName": "Example",
    "lastName": "Person",
    "fullName": "Example Person",
    "status": "ACTIVE",
}


def _client() -> UniFiProtectClient:
    return UniFiProtectClient(auth=ApiKeyAuth("test"), base_url="https://example.invalid")


@pytest.mark.parametrize("family", FAMILIES)
async def test_listing_result_keeps_each_familys_records_and_completeness(family: str) -> None:
    """Every lenient endpoint offers a result without modifying its legacy flag."""
    client = _client()
    client._get = AsyncMock(return_value={"data": [VALID, {"token": "synthetic"}]})
    endpoint = getattr(client, family)
    assert (
        inspect.signature(endpoint.get_all).parameters
        == inspect.signature(endpoint.get_all_result).parameters
    )
    result = await endpoint.get_all_result()
    assert isinstance(result, ProtectListResult)
    assert tuple(record.id for record in result.records) == ("valid",)
    assert result.shape_valid and not result.complete and result.skipped == 1
    assert endpoint.last_result_complete is True


@pytest.mark.parametrize("partial_first", [False, True])
async def test_overlapping_listings_report_their_own_completeness(partial_first: bool) -> None:
    """Completeness is independent of which in-flight request finishes first."""
    client = _client()
    started = [asyncio.Event(), asyncio.Event()]
    finish = [asyncio.Event(), asyncio.Event()]
    calls = 0

    async def respond(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        nonlocal calls
        index = calls
        calls += 1
        started[index].set()
        await finish[index].wait()
        return [{"id": "bridge"}] if index == 0 else [{}]

    client._get = AsyncMock(side_effect=respond)
    async with asyncio.TaskGroup() as group:
        complete_task = group.create_task(client.bridges.get_all_result())
        await started[0].wait()
        partial_task = group.create_task(client.bridges.get_all_result())
        await started[1].wait()
        order = (1, 0) if partial_first else (0, 1)
        tasks = (complete_task, partial_task)
        for index in order:
            finish[index].set()
            await tasks[index]

    assert complete_task.result().complete
    assert [record.id for record in complete_task.result().records] == ["bridge"]
    assert not partial_task.result().complete
    assert partial_task.result().records == ()
    assert partial_task.result().skipped == 1


@pytest.mark.parametrize(
    ("response", "shape_valid"),
    [([], True), ({"data": []}, True), (None, False), ({"data": {}}, False)],
)
async def test_listing_distinguishes_empty_from_unusable(response: Any, shape_valid: bool) -> None:
    """An invalid top-level shape cannot authorize inventory removals."""
    client = _client()
    client._get = AsyncMock(return_value=response)
    endpoint = client.arm_profiles
    endpoint.last_result_complete = False

    result = await endpoint.get_all_result()
    assert (result.records, result.skipped, result.shape_valid, result.complete) == (
        (),
        0,
        shape_valid,
        shape_valid,
    )
    assert endpoint.last_result_complete is False
    assert await endpoint.get_all() == []
    assert endpoint.last_result_complete is True


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (401, UniFiAuthenticationError),
        (404, UniFiNotFoundError),
        (429, UniFiRateLimitError),
        (500, UniFiResponseError),
    ],
)
async def test_listing_result_propagates_http_failure(status: int, error: type[Exception]) -> None:
    """HTTP errors retain their mapped exception rather than returning inventory evidence."""
    with aioresponses() as mock:
        mock.get(
            "https://example.invalid/proxy/protect/integration/v1/bridges",
            status=status,
            headers={"Retry-After": "30"},
        )
        async with _client() as client:
            with pytest.raises(error):
                await client.bridges.get_all_result()


@pytest.mark.parametrize(
    ("failure", "error"),
    [
        (aiohttp.ClientConnectionError("test"), UniFiConnectionError),
        (TimeoutError(), UniFiTimeoutError),
    ],
)
async def test_listing_result_propagates_transport_failure(
    failure: Exception, error: type[Exception]
) -> None:
    """Transport errors do not yield an empty or partial inventory result."""
    with aioresponses() as mock:
        mock.get(
            "https://example.invalid/proxy/protect/integration/v1/bridges",
            exception=failure,
        )
        async with _client() as client:
            with pytest.raises(error):
                await client.bridges.get_all_result()


@pytest.mark.parametrize(("family", "path"), [("users", "users"), ("ulp_users", "ulp-users")])
async def test_protect_user_listing_keeps_personal_data_out_of_transport_logs(
    caplog: pytest.LogCaptureFixture, family: str, path: str
) -> None:
    """Neither listing interface logs user records, even with transport debug enabled."""
    marker = "synthetic-personal-value"
    caplog.set_level(logging.DEBUG, logger="unifi_official_api")
    with aioresponses() as mock:
        mock.get(
            f"https://example.invalid/proxy/protect/integration/v1/{path}",
            payload=[{"id": marker, "email": marker, "firstName": marker}],
            repeat=True,
        )
        async with _client() as client:
            endpoint = getattr(client, family)
            assert (await endpoint.get_all_result()).skipped == 1
            assert await endpoint.get_all() == []
    assert "failed validation" in caplog.text
    assert marker not in caplog.text
