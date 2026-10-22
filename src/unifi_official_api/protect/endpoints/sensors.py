"""Sensors endpoint for UniFi Protect API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from ...validation import require_record, written_record
from ..models import Sensor

if TYPE_CHECKING:
    from ..client import UniFiProtectClient

_LOGGER = logging.getLogger(__name__)


class SensorsEndpoint:
    """Endpoint for managing UniFi Protect sensors."""

    def __init__(self, client: UniFiProtectClient) -> None:
        """
        Initialize the sensors endpoint.

        Args:
            client: The UniFi Protect client.

        """
        self._client = client
        # False when the most recent get_all() silently dropped an item on a
        # ValidationError. Callers need to tell a complete listing from a short
        # one: a device absent because its payload would not parse is still
        # adopted, and must not be treated as removed.
        self.last_result_complete: bool = True

    async def get_all(self, site_id: str | None = None) -> list[Sensor]:
        """
        List all sensors.

        Args:
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            List of sensors.

        """
        path = self._client.build_api_path("/sensors", site_id)
        self.last_result_complete = True
        response = await self._client._get(path)

        if response is None:
            return []

        data = response.get("data", response) if isinstance(response, dict) else response
        if not isinstance(data, list):
            return []

        sensors: list[Sensor] = []
        for item in data:
            try:
                sensors.append(Sensor.model_validate(item))
            except ValidationError as err:
                self.last_result_complete = False
                _LOGGER.warning(
                    "Skipping sensor that failed to parse (id=%s): %s",
                    item.get("id") if isinstance(item, dict) else "?",
                    err,
                )
        return sensors

    async def get(self, sensor_id: str, site_id: str | None = None) -> Sensor:
        """
        Get a specific sensor.

        Args:
            sensor_id: The sensor ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The sensor.

        Raises:
            UniFiNotFoundError: If the response holds no sensor with an ``id``.
            UniFiResponseError: If the sensor in the response fails validation.

        """
        path = self._client.build_api_path(f"/sensors/{sensor_id}", site_id)
        return require_record(await self._client._get(path), Sensor, f"Sensor {sensor_id}")

    async def update(
        self,
        sensor_id: str,
        site_id: str | None = None,
        **kwargs: Any,
    ) -> Sensor:
        """
        Update sensor settings.

        Args:
            sensor_id: The sensor ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).
            **kwargs: Settings to update.

        Returns:
            The updated sensor.

        Raises:
            UniFiNotFoundError: If the follow-up ``get()`` finds no sensor.
            UniFiResponseError: If the follow-up ``get()`` response fails validation.

        """
        path = self._client.build_api_path(f"/sensors/{sensor_id}", site_id)
        written = written_record(await self._client._patch(path, json_data=kwargs), Sensor)
        if written is not None:
            return written
        return await self.get(sensor_id, site_id)

    async def set_status_led(
        self,
        sensor_id: str,
        enabled: bool,
        site_id: str | None = None,
    ) -> Sensor:
        """
        Enable or disable the status LED.

        Args:
            sensor_id: The sensor ID.
            enabled: Whether to enable the LED.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The updated sensor.

        """
        return await self.update(sensor_id, site_id, openStatusLedEnabled=enabled)

    async def set_motion_sensitivity(
        self,
        sensor_id: str,
        sensitivity: int,
        site_id: str | None = None,
    ) -> Sensor:
        """
        Set motion sensitivity.

        Args:
            sensor_id: The sensor ID.
            sensitivity: Sensitivity level (0-100).
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The updated sensor.

        """
        if not 0 <= sensitivity <= 100:
            raise ValueError("Sensitivity must be between 0 and 100")
        return await self.update(sensor_id, site_id, motionSettings={"sensitivity": sensitivity})
