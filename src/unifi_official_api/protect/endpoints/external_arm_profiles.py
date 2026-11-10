"""External alarm manager arm profile endpoint for UniFi Protect API."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from ...validation import created_record, require_record, written_record
from ..models import ExternalArmProfile
from ._listing import ProtectListResult, parse_listing

if TYPE_CHECKING:
    from ..client import UniFiProtectClient

_LOGGER = logging.getLogger(__name__)

_MAX_DELAY_SECONDS = 3600
_RESOURCE = "external arm profile"


class _Unset:
    """Sentinel that keeps an omitted PATCH field distinct from an explicit null."""

    __slots__ = ()


_UNSET = _Unset()


def _validate_title(title: object) -> str:
    """Return a non-empty title, or raise without quoting the rejected value."""
    if not isinstance(title, str) or not title:
        raise ValueError("title must be a non-empty string")
    return title


def _validate_delay(value: object, name: str, *, allow_none: bool) -> int | None:
    """Return an integer delay in 0-3600, reject bools, optionally accept null."""
    if value is None:
        if allow_none:
            return None
        raise ValueError(f"{name} must be an integer from 0 to {_MAX_DELAY_SECONDS}")
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer from 0 to {_MAX_DELAY_SECONDS}")
    if not 0 <= value <= _MAX_DELAY_SECONDS:
        raise ValueError(f"{name} must be an integer from 0 to {_MAX_DELAY_SECONDS}")
    return value


def _validate_pin_code(value: object) -> str | None:
    """Return a 4-6 ASCII digit PIN or null, without quoting the rejected value."""
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or not 4 <= len(value) <= 6
        or not value.isascii()
        or not value.isdigit()
    ):
        raise ValueError("pin_code must be null or an ASCII digit string of 4 to 6 characters")
    return value


def _validate_alarm_ids(value: object, *, allow_none: bool) -> list[str] | None:
    """Return a list of non-empty alarm IDs, optionally accepting null."""
    if value is None:
        if allow_none:
            return None
        raise ValueError("alarm_ids must be a list of non-empty strings")
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError("alarm_ids must be a list of non-empty strings")
    return [item for item in value if isinstance(item, str)]


def _validate_schedule(value: object, *, allow_none: bool) -> dict[str, Any] | None:
    """Return the schedule mapping unchanged in structure, optionally accepting null."""
    if value is None:
        if allow_none:
            return None
        raise ValueError("schedule must be a mapping")
    if not isinstance(value, Mapping):
        raise ValueError("schedule must be a mapping")
    return dict(value)


def _delay_field(value: object, name: str, *, allow_none: bool) -> Any:
    """Validate a supplied delay, passing the unset sentinel through untouched."""
    if isinstance(value, _Unset):
        return value
    return _validate_delay(value, name, allow_none=allow_none)


def _field(
    value: object,
    validate: Any,
    *,
    allow_none: bool,
) -> Any:
    """Validate a supplied field, passing the unset sentinel through untouched."""
    if isinstance(value, _Unset):
        return value
    return validate(value, allow_none=allow_none)


def _pin_field(value: object) -> Any:
    """Validate a supplied PIN field, passing the unset sentinel through untouched."""
    if isinstance(value, _Unset):
        return value
    return _validate_pin_code(value)


def _title_field(value: object) -> Any:
    """Validate a supplied title, passing the unset sentinel through untouched."""
    if isinstance(value, _Unset):
        return value
    return _validate_title(value)


def _payload(**values: Any) -> dict[str, Any]:
    """Return only the fields the caller supplied."""
    return {name: value for name, value in values.items() if not isinstance(value, _Unset)}


class ExternalArmProfilesEndpoint:
    """Endpoint for arm profiles owned by the external alarm manager.

    Every request sends ``log_body=False``: requests and responses may carry a
    write-only ``pin_code``, and response excerpts must never reach a log.
    """

    def __init__(self, client: UniFiProtectClient) -> None:
        """
        Initialize the external arm profiles endpoint.

        Args:
            client: The UniFi Protect client.

        """
        self._client = client
        # False when the most recent get_all() silently dropped an item on a
        # ValidationError; a short listing must not read as removed profiles.
        self.last_result_complete: bool = True

    async def get_all(self, site_id: str | None = None) -> list[ExternalArmProfile]:
        """
        List all external arm profiles.

        Args:
            site_id: Optional site ID accepted for compatibility with other Protect
                endpoints; it is currently ignored.

        Returns:
            List of external arm profiles.

        """
        self.last_result_complete = True
        response = await self._fetch_profiles(site_id)
        return list(
            parse_listing(
                ExternalArmProfile,
                response,
                _RESOURCE,
                _LOGGER,
                legacy_state=self,
            ).records
        )

    async def get_all_result(
        self, site_id: str | None = None
    ) -> ProtectListResult[ExternalArmProfile]:
        """Return external arm profiles and completeness from this request."""
        response = await self._fetch_profiles(site_id)
        return parse_listing(ExternalArmProfile, response, _RESOURCE, _LOGGER)

    async def _fetch_profiles(self, site_id: str | None) -> object:
        """Fetch the listing with response bodies kept out of the transport log."""
        path = self._client.build_api_path("/external/arm-profiles", site_id)
        return await self._client._get(path, log_body=False)

    async def get(self, profile_id: str, site_id: str | None = None) -> ExternalArmProfile:
        """
        Get one external arm profile by ID.

        Args:
            profile_id: The external arm profile ID.
            site_id: Optional site ID accepted for compatibility with other Protect
                endpoints; it is currently ignored.

        Returns:
            The parsed external arm profile.

        Raises:
            UniFiNotFoundError: If the response holds no profile with an ``id``.
            UniFiResponseError: If the profile in the response fails validation.

        """
        path = self._client.build_api_path(f"/external/arm-profiles/{profile_id}", site_id)
        return require_record(
            await self._client._get(path, log_body=False),
            ExternalArmProfile,
            f"External arm profile {profile_id}",
        )

    async def create(
        self,
        title: str,
        site_id: str | None = None,
        *,
        activation_delay: int | _Unset | None = _UNSET,
        deactivation_delay: int | _Unset | None = _UNSET,
        schedule: Mapping[str, Any] | _Unset | None = _UNSET,
        alarm_ids: list[str] | _Unset | None = _UNSET,
        pin_code: str | _Unset | None = _UNSET,
    ) -> ExternalArmProfile:
        """
        Create an external arm profile.

        Only the fields the caller supplies are sent.

        Args:
            title: The profile title (required).
            site_id: Optional site ID accepted for compatibility with other Protect
                endpoints; it is currently ignored.
            activation_delay: Delay in seconds from 0 to 3600.
            deactivation_delay: Delay in seconds from 0 to 3600.
            schedule: Weekly schedule passed through without local structure checks.
            alarm_ids: Non-empty alarm IDs included in the profile.
            pin_code: Write-only PIN of 4 to 6 digits, or null.

        Returns:
            The created external arm profile.

        Raises:
            ValueError: If a supplied field fails local validation.
            UniFiResponseError: If the console accepted the request but the
                response holds no valid profile. The profile may have been created.

        """
        body = _payload(
            title=_validate_title(title),
            activation_delay=_delay_field(activation_delay, "activation_delay", allow_none=False),
            deactivation_delay=_delay_field(
                deactivation_delay, "deactivation_delay", allow_none=False
            ),
            schedule=_field(schedule, _validate_schedule, allow_none=False),
            alarm_ids=_field(alarm_ids, _validate_alarm_ids, allow_none=False),
            pin_code=_pin_field(pin_code),
        )
        path = self._client.build_api_path("/external/arm-profiles", site_id)
        response = await self._client._post(path, json_data=body, log_body=False)
        return created_record(response, ExternalArmProfile, "External arm profile")

    async def update(
        self,
        profile_id: str,
        site_id: str | None = None,
        *,
        title: str | _Unset = _UNSET,
        activation_delay: int | _Unset | None = _UNSET,
        deactivation_delay: int | _Unset | None = _UNSET,
        schedule: Mapping[str, Any] | _Unset | None = _UNSET,
        alarm_ids: list[str] | _Unset | None = _UNSET,
        pin_code: str | _Unset | None = _UNSET,
    ) -> ExternalArmProfile:
        """
        Partially update an external arm profile.

        Omitted fields stay unchanged; a nullable field sent as ``None`` is
        cleared.

        Args:
            profile_id: The external arm profile ID.
            site_id: Optional site ID accepted for compatibility with other Protect
                endpoints; it is currently ignored.
            title: A new non-empty title. A title cannot be cleared.
            activation_delay: New delay in seconds, or null to clear it.
            deactivation_delay: New delay in seconds, or null to clear it.
            schedule: New schedule, or null to clear it.
            alarm_ids: New alarm IDs, or null to clear them.
            pin_code: New PIN of 4 to 6 digits, or null to clear it.

        Returns:
            The updated external arm profile: from the ``PATCH`` response when it
            holds a valid profile, otherwise from a follow-up ``get()``.

        Raises:
            ValueError: If no field is supplied, or a supplied field fails local
                validation. No request is sent.
            UniFiNotFoundError: If the follow-up ``get()`` finds no profile.
            UniFiResponseError: If the follow-up ``get()`` response fails validation.

        """
        body = _payload(
            title=_title_field(title),
            activation_delay=_delay_field(activation_delay, "activation_delay", allow_none=True),
            deactivation_delay=_delay_field(
                deactivation_delay, "deactivation_delay", allow_none=True
            ),
            schedule=_field(schedule, _validate_schedule, allow_none=True),
            alarm_ids=_field(alarm_ids, _validate_alarm_ids, allow_none=True),
            pin_code=_pin_field(pin_code),
        )
        if not body:
            raise ValueError("update requires at least one field")
        path = self._client.build_api_path(f"/external/arm-profiles/{profile_id}", site_id)
        written = written_record(
            await self._client._patch(path, json_data=body, log_body=False),
            ExternalArmProfile,
        )
        if written is not None:
            return written
        return await self.get(profile_id, site_id)

    async def arm(self, profile_id: str, site_id: str | None = None) -> ExternalArmProfile:
        """
        Arm one external arm profile.

        Args:
            profile_id: The external arm profile ID.
            site_id: Optional site ID accepted for compatibility with other Protect
                endpoints; it is currently ignored.

        Returns:
            The updated external arm profile: from the action response when it
            holds a valid profile, otherwise from a follow-up ``get()``.

        Raises:
            UniFiNotFoundError: If the follow-up ``get()`` finds no profile.
            UniFiResponseError: If the follow-up ``get()`` response fails validation.

        """
        return await self._action(profile_id, "arm", site_id)

    async def disarm(self, profile_id: str, site_id: str | None = None) -> ExternalArmProfile:
        """
        Disarm one external arm profile.

        Args:
            profile_id: The external arm profile ID.
            site_id: Optional site ID accepted for compatibility with other Protect
                endpoints; it is currently ignored.

        Returns:
            The updated external arm profile: from the action response when it
            holds a valid profile, otherwise from a follow-up ``get()``.

        Raises:
            UniFiNotFoundError: If the follow-up ``get()`` finds no profile.
            UniFiResponseError: If the follow-up ``get()`` response fails validation.

        """
        return await self._action(profile_id, "disarm", site_id)

    async def _action(
        self, profile_id: str, action: str, site_id: str | None
    ) -> ExternalArmProfile:
        """POST an arm or disarm action with no body, then echo or re-fetch."""
        path = self._client.build_api_path(
            f"/external/arm-profiles/{profile_id}/actions/{action}", site_id
        )
        written = written_record(await self._client._post(path, log_body=False), ExternalArmProfile)
        if written is not None:
            return written
        return await self.get(profile_id, site_id)

    async def delete(self, profile_id: str, site_id: str | None = None) -> bool:
        """
        Delete an external arm profile.

        Args:
            profile_id: The external arm profile ID.
            site_id: Optional site ID accepted for compatibility with other Protect
                endpoints; it is currently ignored.

        Returns:
            True if successful.

        """
        path = self._client.build_api_path(f"/external/arm-profiles/{profile_id}", site_id)
        await self._client._delete(path, log_body=False)
        return True
