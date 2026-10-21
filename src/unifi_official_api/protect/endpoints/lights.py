"""Lights endpoint for UniFi Protect API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from ...validation import require_record, written_record
from ..models import Light, LightMode

if TYPE_CHECKING:
    from ..client import UniFiProtectClient

_LOGGER = logging.getLogger(__name__)

MIN_LED_LEVEL = 1
MAX_LED_LEVEL = 6


class LightsEndpoint:
    """Endpoint for managing UniFi Protect lights."""

    def __init__(self, client: UniFiProtectClient) -> None:
        """
        Initialize the lights endpoint.

        Args:
            client: The UniFi Protect client.

        """
        self._client = client
        # False when the most recent get_all() silently dropped an item on a
        # ValidationError. Callers need to tell a complete listing from a short
        # one: a device absent because its payload would not parse is still
        # adopted, and must not be treated as removed.
        self.last_result_complete: bool = True

    async def get_all(self, site_id: str | None = None) -> list[Light]:
        """
        List all lights.

        Args:
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            List of lights.

        """
        path = self._client.build_api_path("/lights", site_id)
        self.last_result_complete = True
        response = await self._client._get(path)

        if response is None:
            return []

        data = response.get("data", response) if isinstance(response, dict) else response
        if not isinstance(data, list):
            return []

        lights: list[Light] = []
        for item in data:
            try:
                lights.append(Light.model_validate(item))
            except ValidationError as err:
                self.last_result_complete = False
                _LOGGER.warning(
                    "Skipping light that failed to parse (id=%s): %s",
                    item.get("id") if isinstance(item, dict) else "?",
                    err,
                )
        return lights

    async def get(self, light_id: str, site_id: str | None = None) -> Light:
        """
        Get a specific light.

        Args:
            light_id: The light ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The light.

        Raises:
            UniFiNotFoundError: If the response holds no light with an ``id``.
            UniFiResponseError: If the light in the response fails validation.

        """
        path = self._client.build_api_path(f"/lights/{light_id}", site_id)
        return require_record(await self._client._get(path), Light, f"Light {light_id}")

    async def update(
        self,
        light_id: str,
        site_id: str | None = None,
        **kwargs: Any,
    ) -> Light:
        """
        Update light settings.

        Args:
            light_id: The light ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).
            **kwargs: Settings to update.

        Returns:
            The updated light.

        Raises:
            UniFiNotFoundError: If the follow-up ``get()`` finds no light.
            UniFiResponseError: If the follow-up ``get()`` response fails validation.

        """
        path = self._client.build_api_path(f"/lights/{light_id}", site_id)
        written = written_record(await self._client._patch(path, json_data=kwargs), Light)
        if written is not None:
            return written
        return await self.get(light_id, site_id)

    async def turn_on(self, light_id: str, site_id: str | None = None) -> Light:
        """
        Turn on a light.

        Args:
            light_id: The light ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The updated light.

        """
        return await self.update(light_id, site_id, lightModeSettings={"mode": "always"})

    async def turn_off(self, light_id: str, site_id: str | None = None) -> Light:
        """
        Turn off a light.

        Args:
            light_id: The light ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The updated light.

        """
        return await self.update(light_id, site_id, lightModeSettings={"mode": "off"})

    async def set_mode(
        self,
        light_id: str,
        mode: LightMode | str,
        site_id: str | None = None,
    ) -> Light:
        """
        Set light mode.

        Args:
            light_id: The light ID.
            mode: The light mode.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The updated light.

        """
        mode_val = mode.value if hasattr(mode, "value") else str(mode)
        if mode_val == "on":
            mode_val = "always"
        return await self.update(light_id, site_id, lightModeSettings={"mode": mode_val})

    async def set_brightness(
        self,
        light_id: str,
        led_level: int,
        site_id: str | None = None,
    ) -> Light:
        """
        Set light brightness.

        Args:
            light_id: The light ID.
            led_level: Brightness level (1-6).
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The updated light.

        """
        if (
            not isinstance(led_level, int)
            or isinstance(led_level, bool)
            or not (MIN_LED_LEVEL <= led_level <= MAX_LED_LEVEL)
        ):
            raise ValueError("led_level must be between 1 and 6")
        return await self.update(
            light_id,
            site_id,
            lightDeviceSettings={"ledLevel": led_level},
        )
