"""Arm profile endpoint for UniFi Protect API."""

from __future__ import annotations

import contextlib
import json
import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from ...exceptions import (
    UniFiGlobalAlarmManagerError,
    UniFiNotFoundError,
    UniFiResponseError,
)
from ...validation import created_record, parse_record, response_record, written_record
from ..models import ArmProfile, ArmProfileSettings

if TYPE_CHECKING:
    from ..client import UniFiProtectClient

_LOGGER = logging.getLogger(__name__)

# Protect answers an arm/disarm request, and a listing of the arm profiles,
# with HTTP 400 and a body such as
# {"name": "BAD_REQUEST", "error": "This operation is not available when
# global alarm manager is enabled"} while the UniFi global alarm manager owns
# the alarm. Matching the body keeps every other 400 a plain response error.
_GLOBAL_ALARM_MANAGER_MARKER = "global alarm manager"


def _json_strings(value: Any) -> list[str]:
    """Return every string in a decoded JSON document, keys included."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for k, v in value.items() for s in (*_json_strings(k), *_json_strings(v))]
    if isinstance(value, list):
        return [s for item in value for s in _json_strings(item)]
    return []


def _mentions_global_alarm_manager(body: str | None) -> bool:
    """
    Return whether a response body says the global alarm manager is the cause.

    The whole text is searched, not one field of it, because the body is
    whatever the console, or the cloud connector in front of it for a REMOTE
    entry, sent. The REMOTE client does no unwrapping of its own: it hands the
    connector's response text through as ``response_body`` like a local one, so
    the message can sit under any nesting. The strings of a JSON body are
    searched as well as its raw text, which also covers a message that is
    escaped, or is itself a JSON document inside a string. The wording is
    compared without case and with "_", "-" and runs of spaces read as one
    space, so ``GLOBAL_ALARM_MANAGER_ENABLED`` matches too.
    """
    if not body:
        return False
    texts = [body]
    with contextlib.suppress(ValueError):
        texts.extend(_json_strings(json.loads(body)))
    return any(
        _GLOBAL_ALARM_MANAGER_MARKER
        in " ".join(text.lower().replace("_", " ").replace("-", " ").split())
        for text in texts
    )


def _raise_for_global_alarm_manager(err: UniFiResponseError) -> None:
    """Re-raise Protect's "global alarm manager is enabled" 400 as its own type."""
    if err.status_code == HTTPStatus.BAD_REQUEST and _mentions_global_alarm_manager(
        err.response_body
    ):
        raise UniFiGlobalAlarmManagerError(err.message, err.status_code, err.response_body) from err


class ArmProfilesEndpoint:
    """Endpoint for managing UniFi Protect arm profiles."""

    def __init__(self, client: UniFiProtectClient) -> None:
        """
        Initialize the arm profiles endpoint.

        Args:
            client: The UniFi Protect client.

        """
        self._client = client
        # False when the most recent get_all() silently dropped an item on a
        # ValidationError. Callers need to tell a complete listing from a short
        # one: a device absent because its payload would not parse is still
        # adopted, and must not be treated as removed.
        self.last_result_complete: bool = True

    async def get_all(self, site_id: str | None = None) -> list[ArmProfile]:
        """
        List all arm profiles.

        Args:
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            List of arm profiles.

        Raises:
            UniFiGlobalAlarmManagerError: If the global alarm manager owns the
                alarm. Protect refuses to list arm profiles then, which makes
                this read-only call a way to tell that it is enabled.

        """
        self.last_result_complete = True
        profiles: list[ArmProfile] = []
        for item in await self._get_raw_profiles(site_id):
            try:
                profiles.append(ArmProfile.model_validate(item))
            except ValidationError as err:
                self.last_result_complete = False
                _LOGGER.warning(
                    "Skipping arm profile that failed to parse (id=%s): %s",
                    item.get("id") if isinstance(item, dict) else "?",
                    err,
                )
        return profiles

    async def _get_raw_profiles(self, site_id: str | None) -> list[Any]:
        """Return the unvalidated items of the arm profile listing."""
        path = self._client.build_api_path("/arm-profiles", site_id)
        try:
            response = await self._client._get(path)
        except UniFiResponseError as err:
            _raise_for_global_alarm_manager(err)
            raise

        if response is None:
            return []

        data = response.get("data", response) if isinstance(response, dict) else response
        return data if isinstance(data, list) else []

    async def create(
        self,
        site_id: str | None = None,
        **kwargs: Any,
    ) -> ArmProfile:
        """
        Create a new arm profile.

        Args:
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).
            **kwargs: Arm profile payload fields.

        Returns:
            The created arm profile.

        Raises:
            TypeError: If ``site_id`` is neither a string nor ``None``.
            UniFiResponseError: If the console accepted the request but the response
                holds no valid arm profile. The profile may have been created.

        """
        if site_id is not None and not isinstance(site_id, str):
            msg = (
                f"site_id must be a str or None, not {type(site_id).__name__}; "
                "pass settings as keyword arguments"
            )
            raise TypeError(msg)
        path = self._client.build_api_path("/arm-profiles", site_id)
        response = await self._client._post(path, json_data=kwargs)
        return created_record(response, ArmProfile, "Arm profile")

    async def update(
        self,
        arm_profile_id: str,
        site_id: str | None = None,
        **kwargs: Any,
    ) -> ArmProfile:
        """
        Update an arm profile.

        Args:
            arm_profile_id: The arm profile ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).
            **kwargs: Settings to update.

        Returns:
            The updated arm profile.

        Raises:
            TypeError: If ``site_id`` is neither a string nor ``None``.
            UniFiNotFoundError: If the update response holds no arm profile and the
                follow-up listing has none with this ID.
            UniFiResponseError: If the update response holds no valid arm profile and
                the profile in the follow-up listing fails validation.
            UniFiGlobalAlarmManagerError: If the follow-up listing is refused because
                the global alarm manager owns the alarm.

        """
        if site_id is not None and not isinstance(site_id, str):
            msg = (
                f"site_id must be a str or None, not {type(site_id).__name__}; "
                "pass settings as keyword arguments"
            )
            raise TypeError(msg)
        path = self._client.build_api_path(f"/arm-profiles/{arm_profile_id}", site_id)
        written = written_record(await self._client._patch(path, json_data=kwargs), ArmProfile)
        if written is not None:
            return written
        # The spec has no single-profile GET, so the listing is searched. Its raw
        # items are, not get_all(), which skips a profile that fails validation:
        # that profile exists and must not read as missing.
        for item in await self._get_raw_profiles(site_id):
            if isinstance(item, dict) and item.get("id") == arm_profile_id:
                return parse_record(ArmProfile, item, f"Arm profile {arm_profile_id}")
        msg = f"Arm profile {arm_profile_id} not found"
        raise UniFiNotFoundError(msg, status_code=200)

    async def delete(self, arm_profile_id: str, site_id: str | None = None) -> bool:
        """
        Delete an arm profile.

        Args:
            arm_profile_id: The arm profile ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            True if successful.

        """
        path = self._client.build_api_path(f"/arm-profiles/{arm_profile_id}", site_id)
        await self._client._delete(path)
        return True

    async def enable(self, site_id: str | None = None, **kwargs: Any) -> bool:
        """
        Enable arm profiles.

        Args:
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).
            **kwargs: Optional request payload fields.

        Returns:
            True if the request was accepted.

        Raises:
            UniFiGlobalAlarmManagerError: If the global alarm manager owns the
                alarm and Protect refuses the request.

        """
        path = self._client.build_api_path("/arm-profiles/enable", site_id)
        try:
            await self._client._post(path, json_data=kwargs or None)
        except UniFiResponseError as err:
            _raise_for_global_alarm_manager(err)
            raise
        return True

    async def disable(self, site_id: str | None = None, **kwargs: Any) -> bool:
        """
        Disable arm profiles.

        Args:
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).
            **kwargs: Optional request payload fields.

        Returns:
            True if the request was accepted.

        Raises:
            UniFiGlobalAlarmManagerError: If the global alarm manager owns the
                alarm and Protect refuses the request.

        """
        path = self._client.build_api_path("/arm-profiles/disable", site_id)
        try:
            await self._client._post(path, json_data=kwargs or None)
        except UniFiResponseError as err:
            _raise_for_global_alarm_manager(err)
            raise
        return True

    async def update_settings(
        self,
        site_id: str | None = None,
        **kwargs: Any,
    ) -> ArmProfileSettings | bool:
        """
        Update global arm profile settings.

        Args:
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).
            **kwargs: Settings to update.

        Returns:
            ArmProfileSettings if returned by the API, or True if request accepted.

        Raises:
            TypeError: If ``site_id`` is neither a string nor ``None``.

        """
        if site_id is not None and not isinstance(site_id, str):
            msg = (
                f"site_id must be a str or None, not {type(site_id).__name__}; "
                "pass settings as keyword arguments"
            )
            raise TypeError(msg)
        path = self._client.build_api_path("/arm-profiles/settings", site_id)
        response = await self._client._patch(path, json_data=kwargs or None)

        data = response_record(response, id_key=None)
        if data is not None and ("activeProfileId" in data or "isArmed" in data):
            settings = written_record(data, ArmProfileSettings, id_key=None)
            if settings is not None:
                return settings
        return True
