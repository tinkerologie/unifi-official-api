# Copyright 2026 UniFi Insights contributors
"""Tests for speaker stop-siren and external arm manager arm profiles."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Any

import pytest
from yarl import URL

from unifi_official_api import ApiKeyAuth, ConnectionType, LocalAuth
from unifi_official_api.exceptions import (
    UniFiNotFoundError,
    UniFiResponseError,
)
from unifi_official_api.protect import (
    ExternalArmProfile,
    ExternalArmProfileState,
    UniFiProtectClient,
)

LOCAL_BASE = "https://192.168.1.1/proxy/protect/integration/v1"
REMOTE_BASE = "https://api.ui.com/v1/connector/consoles/console-1/protect/integration/v1"
PROFILE_PATH = f"{LOCAL_BASE}/external/arm-profiles"


class _Response:
    """Minimal aiohttp response double."""

    def __init__(
        self,
        body: Any = None,
        status: int = 200,
        *,
        raw: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._body = body
        self._raw = raw
        self.status = status
        self.headers = headers or {}
        self.history: tuple[Any, ...] = ()
        self.url = URL("https://192.168.1.1/proxy/protect/integration/v1/external/arm-profiles")
        self.method = "GET"

    async def __aenter__(self) -> _Response:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def text(self) -> str:
        """Return the response text as the transport would."""
        if self._raw is not None:
            return self._raw
        return "" if self._body is None else json.dumps(self._body)

    async def json(self) -> Any:
        """Return the decoded JSON body, or raise for a malformed body."""
        if self._raw is not None:
            raise ValueError("not JSON")
        if self._body is None:
            raise ValueError("no body")
        return self._body


class _Session:
    """Recording session that replays queued responses."""

    closed = False

    def __init__(self, *responses: _Response) -> None:
        self._responses: Iterator[_Response] = iter(responses)
        self.requests: list[dict[str, Any]] = []

    def request(self, method: str, url: object, **kwargs: Any) -> _Response:
        """Record a request and return the next queued response."""
        self.requests.append({"method": method, "url": str(url), **kwargs})
        return next(self._responses)

    async def close(self) -> None:
        """Mark the session closed."""
        self.closed = True


def _local(*responses: _Response) -> tuple[UniFiProtectClient, _Session]:
    session = _Session(*responses)
    client = UniFiProtectClient(
        auth=LocalAuth(api_key="key", verify_ssl=False),
        base_url="https://192.168.1.1",
        session=session,  # type: ignore[arg-type]
    )
    return client, session


def _remote(*responses: _Response) -> tuple[UniFiProtectClient, _Session]:
    session = _Session(*responses)
    client = UniFiProtectClient(
        auth=ApiKeyAuth(api_key="key"),
        connection_type=ConnectionType.REMOTE,
        console_id="console-1",
        session=session,  # type: ignore[arg-type]
    )
    return client, session


_PROFILE = {"id": "profile-1"}


class TestStopSiren:
    """``SpeakersEndpoint.stop_siren`` mirrors ``test_sound``."""

    @pytest.mark.parametrize(
        ("client_factory", "base"),
        [(_local, LOCAL_BASE), (_remote, REMOTE_BASE)],
        ids=["local", "remote"],
    )
    async def test_posts_to_stop_siren_and_returns_true(
        self, client_factory: Any, base: str
    ) -> None:
        """The action posts to the documented path on both routes."""
        client, session = client_factory(_Response(status=204))

        assert await client.speakers.stop_siren("speaker-1") is True

        request = session.requests[0]
        assert (request["method"], request["url"]) == (
            "POST",
            f"{base}/speakers/speaker-1/stop-siren",
        )
        assert request["json"] is None

    async def test_http_400_raises_response_error(self) -> None:
        """A speaker that is offline or too old is a response error."""
        client, _session = _local(_Response({"error": "speaker offline"}, status=400))

        with pytest.raises(UniFiResponseError) as caught:
            await client.speakers.stop_siren("speaker-1")

        assert caught.value.status_code == 400


class TestExternalArmProfileReads:
    """Listing and single-record reads."""

    @pytest.mark.parametrize(
        ("response", "ids", "complete", "skipped"),
        [
            ([{"id": "a"}], ["a"], True, 0),
            ({"data": [{"id": "a"}]}, ["a"], True, 0),
            ([{"id": "a"}, {"title": "no id"}], ["a"], False, 1),
            ({"data": {}}, [], False, 0),
            (None, [], False, 0),
        ],
        ids=["bare-list", "data-list", "skipped", "bad-shape", "none"],
    )
    async def test_listings_report_completeness(
        self, response: Any, ids: list[str], complete: bool, skipped: int
    ) -> None:
        """Every response shape carries its own completeness evidence."""
        client, _session = _local(_Response(response))

        result = await client.external_arm_profiles.get_all_result()

        assert result.complete is complete
        assert result.skipped == skipped
        assert [record.id for record in result.records] == ids

    async def test_get_all_keeps_the_legacy_completeness_flag(self) -> None:
        """A short listing sets ``last_result_complete`` to False."""
        client, session = _local(_Response([{"id": "a"}, {"title": "bad"}]))

        assert [profile.id for profile in await client.external_arm_profiles.get_all()] == ["a"]
        assert client.external_arm_profiles.last_result_complete is False
        assert session.requests[0]["url"] == PROFILE_PATH

    async def test_get_missing_record_is_not_found(self) -> None:
        """A response without a profile ID is a not-found result."""
        client, _session = _local(_Response({"data": {}}))

        with pytest.raises(UniFiNotFoundError):
            await client.external_arm_profiles.get("profile-1")

    async def test_get_invalid_record_is_a_sanitised_response_error(self) -> None:
        """Validation failures name fields, never values."""
        marker = "synthetic-rejected-value"
        client, _session = _local(_Response({"id": 123, "title": marker}))

        with pytest.raises(UniFiResponseError) as caught:
            await client.external_arm_profiles.get("profile-1")

        assert caught.value.status_code == 200
        assert marker not in caught.value.message
        assert "id" in caught.value.message


class TestExternalArmProfileWrites:
    """Create, update, arm, disarm and delete."""

    async def test_create_sends_only_supplied_fields(self) -> None:
        """Omitted optional fields never reach the request body."""
        client, session = _local(_Response({"id": "profile-1", "title": "Home"}))

        created = await client.external_arm_profiles.create("Home", pin_code="483920")

        assert isinstance(created, ExternalArmProfile)
        assert created.id == "profile-1"
        request = session.requests[0]
        assert (request["method"], request["url"]) == ("POST", PROFILE_PATH)
        assert request["json"] == {"title": "Home", "pin_code": "483920"}

    async def test_create_sends_every_supplied_field(self) -> None:
        """A full create sends delays, schedule and alarm IDs unchanged."""
        client, session = _local(_Response(_PROFILE))
        schedule = {"mon": {"type": "all_day"}}

        await client.external_arm_profiles.create(
            "Home",
            activation_delay=30,
            deactivation_delay=0,
            schedule=schedule,
            alarm_ids=["alarm-1"],
            pin_code=None,
        )

        assert session.requests[0]["json"] == {
            "title": "Home",
            "activation_delay": 30,
            "deactivation_delay": 0,
            "schedule": schedule,
            "alarm_ids": ["alarm-1"],
            "pin_code": None,
        }

    @pytest.mark.parametrize(
        "field",
        ["activation_delay", "deactivation_delay", "schedule", "alarm_ids"],
    )
    async def test_create_rejects_explicit_nulls(self, field: str) -> None:
        """A create cannot clear a field that does not exist yet."""
        client, session = _local()

        with pytest.raises(ValueError):
            await client.external_arm_profiles.create("Home", **{field: None})

        assert session.requests == []

    async def test_create_empty_echo_reports_it_may_have_been_created(self) -> None:
        """A create cannot re-fetch without an ID, so an empty echo is an error."""
        client, _session = _local(_Response(status=204))

        with pytest.raises(UniFiResponseError) as caught:
            await client.external_arm_profiles.create("Home")

        assert "may have been created" in caught.value.message

    async def test_update_distinguishes_omitted_from_null(self) -> None:
        """Omitted fields are retained; explicit nulls are sent to clear them."""
        omitted_client, omitted_session = _local(_Response(_PROFILE))
        await omitted_client.external_arm_profiles.update("profile-1", title="Updated")
        assert omitted_session.requests[0]["json"] == {"title": "Updated"}

        null_client, null_session = _local(_Response(_PROFILE))
        await null_client.external_arm_profiles.update(
            "profile-1",
            activation_delay=None,
            deactivation_delay=None,
            alarm_ids=None,
            schedule=None,
            pin_code=None,
        )
        assert null_session.requests[0]["json"] == {
            "activation_delay": None,
            "deactivation_delay": None,
            "alarm_ids": None,
            "schedule": None,
            "pin_code": None,
        }

    async def test_update_with_no_fields_fails_before_io(self) -> None:
        """An empty PATCH is rejected without a request."""
        client, session = _local()

        with pytest.raises(ValueError, match="at least one field"):
            await client.external_arm_profiles.update("profile-1")

        assert session.requests == []

    async def test_update_echo_returns_the_written_profile(self) -> None:
        """A valid echo is returned without a re-fetch."""
        client, session = _local(
            _Response({"id": "profile-1", "title": "Updated", "state": "armed"})
        )

        profile = await client.external_arm_profiles.update("profile-1", title="Updated")

        assert profile.title == "Updated"
        assert profile.state is ExternalArmProfileState.ARMED
        assert len(session.requests) == 1

    async def test_update_missing_echo_refetches(self) -> None:
        """A bodyless PATCH falls back to ``get``."""
        client, session = _local(_Response(status=204), _Response(_PROFILE))

        profile = await client.external_arm_profiles.update("profile-1", title="Updated")

        assert profile.id == "profile-1"
        assert [(r["method"], r["url"]) for r in session.requests] == [
            ("PATCH", f"{PROFILE_PATH}/profile-1"),
            ("GET", f"{PROFILE_PATH}/profile-1"),
        ]

    @pytest.mark.parametrize("action", ["arm", "disarm"])
    async def test_actions_post_without_a_body_and_echo(self, action: str) -> None:
        """Arm and disarm send no JSON body and return the echoed profile."""
        client, session = _local(_Response({"id": "profile-1", "state": "armed"}))

        profile = await getattr(client.external_arm_profiles, action)("profile-1")

        assert profile.id == "profile-1"
        request = session.requests[0]
        assert request["method"] == "POST"
        assert request["url"] == f"{PROFILE_PATH}/profile-1/actions/{action}"
        assert request["json"] is None

    @pytest.mark.parametrize("action", ["arm", "disarm"])
    async def test_actions_missing_echo_refetch(self, action: str) -> None:
        """A bodyless action response falls back to ``get``."""
        client, session = _local(_Response(status=204), _Response(_PROFILE))

        profile = await getattr(client.external_arm_profiles, action)("profile-1")

        assert profile.id == "profile-1"
        assert [r["method"] for r in session.requests] == ["POST", "GET"]

    async def test_delete_returns_true(self) -> None:
        """Delete accepts the documented 204 response."""
        client, session = _local(_Response(status=204))

        assert await client.external_arm_profiles.delete("profile-1") is True
        assert (session.requests[0]["method"], session.requests[0]["url"]) == (
            "DELETE",
            f"{PROFILE_PATH}/profile-1",
        )


class TestExternalArmProfileValidation:
    """Invalid input fails locally, before any request."""

    @pytest.mark.parametrize(
        "title",
        ["", 123, None],
        ids=["empty", "not-str", "none"],
    )
    async def test_invalid_title(self, title: Any) -> None:
        client, session = _local()

        with pytest.raises(ValueError, match="title"):
            await client.external_arm_profiles.create(title)  # type: ignore[arg-type]

        assert session.requests == []

    @pytest.mark.parametrize(
        "delay",
        [True, False, -1, 3601, "30", 1.5],
        ids=["true", "false", "negative", "too-large", "str", "float"],
    )
    async def test_invalid_delays(self, delay: Any) -> None:
        client, session = _local()

        with pytest.raises(ValueError, match="must be an integer"):
            await client.external_arm_profiles.create("Home", activation_delay=delay)

        assert session.requests == []

    @pytest.mark.parametrize(
        "pin_code",
        ["123", "1234567", "12a45", 483920, "\uff11\uff12\uff13\uff14"],
        ids=["too-short", "too-long", "not-digits", "not-str", "unicode-digits"],
    )
    async def test_invalid_pin_never_appears_in_the_error(self, pin_code: Any) -> None:
        client, session = _local()

        with pytest.raises(ValueError) as caught:
            await client.external_arm_profiles.create("Home", pin_code=pin_code)

        assert str(pin_code) not in str(caught.value)
        assert "pin_code" in str(caught.value)
        assert session.requests == []

    @pytest.mark.parametrize(
        "alarm_ids",
        [["ok", ""], ["ok", 3], "alarm-1"],
        ids=["empty-item", "non-str-item", "not-a-list"],
    )
    async def test_invalid_alarm_ids(self, alarm_ids: Any) -> None:
        client, session = _local()

        with pytest.raises(ValueError, match="alarm_ids"):
            await client.external_arm_profiles.create("Home", alarm_ids=alarm_ids)

        assert session.requests == []

    @pytest.mark.parametrize("schedule", [[], "all-day"])
    async def test_create_invalid_schedule(self, schedule: Any) -> None:
        client, session = _local()

        with pytest.raises(ValueError, match="schedule"):
            await client.external_arm_profiles.create("Home", schedule=schedule)

        assert session.requests == []

    async def test_update_rejects_none_title(self) -> None:
        client, session = _local()

        with pytest.raises(ValueError, match="title"):
            await client.external_arm_profiles.update("profile-1", title=None)  # type: ignore[arg-type]

        assert session.requests == []


class TestExternalArmProfileNonDisclosure:
    """PIN markers never reach logs or model representations."""

    _MARKER = "915273"

    def _assert_silent(self, caplog: pytest.LogCaptureFixture) -> None:
        assert self._MARKER not in caplog.text
        assert "<body omitted" in caplog.text

    async def test_successful_create_omits_the_response_body(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.DEBUG, logger="unifi_official_api")
        client, _session = _local(
            _Response({"id": "profile-1", "has_pin": True, "pin_code": self._MARKER})
        )

        profile = await client.external_arm_profiles.create("Home", pin_code=self._MARKER)

        self._assert_silent(caplog)
        assert self._MARKER not in repr(profile)
        assert self._MARKER not in profile.model_dump_json()
        assert profile.has_pin is True

    async def test_update_http_error_omits_the_response_body(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.DEBUG, logger="unifi_official_api")
        client, _session = _local(
            _Response(
                raw=json.dumps({"error": "bad pin", "pin_code": self._MARKER}),
                status=400,
            )
        )

        with pytest.raises(UniFiResponseError) as caught:
            await client.external_arm_profiles.update("profile-1", pin_code=self._MARKER)

        self._assert_silent(caplog)
        assert self._MARKER not in caught.value.message

    async def test_malformed_success_omits_the_response_body(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.DEBUG, logger="unifi_official_api")
        client, _session = _local(
            _Response(raw=f'<html>"pin_code": "{self._MARKER}"</html>', status=200)
        )

        with pytest.raises(UniFiResponseError):
            await client.external_arm_profiles.update("profile-1", pin_code=self._MARKER)

        self._assert_silent(caplog)

    async def test_listing_omits_the_response_body(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level(logging.DEBUG, logger="unifi_official_api")
        client, _session = _local(_Response([{"id": "profile-1", "pin": self._MARKER}]))

        profiles = await client.external_arm_profiles.get_all()

        self._assert_silent(caplog)
        assert self._MARKER not in repr(profiles[0])

    async def test_refetch_fallback_omits_the_response_body(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The follow-up GET after a bodyless write keeps bodies out of logs."""
        caplog.set_level(logging.DEBUG, logger="unifi_official_api")
        client, _session = _local(
            _Response(status=204),
            _Response({"id": "profile-1", "pin_code": self._MARKER}),
        )

        profile = await client.external_arm_profiles.update("profile-1", pin_code=self._MARKER)

        self._assert_silent(caplog)
        assert self._MARKER not in repr(profile)
