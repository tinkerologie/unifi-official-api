"""Application and file management endpoints for UniFi Protect API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import aiohttp

from ..models.files import ApplicationInfo, DeviceFile, FileType
from ..models.pos import PosTransactionRequest, PosTransactionResponse

if TYPE_CHECKING:
    from ..client import UniFiProtectClient


class ApplicationEndpoint:
    """Endpoint for Protect application metadata, files, and alarm webhooks."""

    def __init__(self, client: UniFiProtectClient) -> None:
        """Initialize the application endpoint."""
        self._client = client

    async def get_info(
        self,
        site_id: str | None = None,
    ) -> ApplicationInfo:
        """Get Protect application version and metadata.

        Args:
            site_id: Optional site ID (unused in local API).

        Returns:
            ApplicationInfo object with version details.

        Raises:
            ValueError: If response is invalid.

        """
        path = self._client.build_api_path("/meta/info", site_id)
        response = await self._client._get(path)

        if response is None:
            raise ValueError("Failed to get application info")

        data = (
            response.get("data", response)
            if isinstance(response, dict) and "data" in response
            else response
        )
        if not isinstance(data, dict) or not data:
            raise ValueError("Failed to get application info")
        return ApplicationInfo.model_validate(data)

    async def get_files(
        self,
        file_type: FileType | str = FileType.ANIMATIONS,
        site_id: str | None = None,
    ) -> list[DeviceFile]:
        """List device asset files of a given type.

        Args:
            file_type: File type (animations or sounds).
            site_id: Optional site ID (unused in local API).

        Returns:
            List of DeviceFile objects.

        """
        ft = file_type.value if isinstance(file_type, FileType) else file_type
        path = self._client.build_api_path(f"/files/{ft}", site_id)
        response = await self._client._get(path)

        if response is None:
            return []

        items = response.get("data", []) if isinstance(response, dict) else response
        if not isinstance(items, list):
            return []

        return [DeviceFile.model_validate(item) for item in items]

    async def upload_file(
        self,
        file_data: bytes | None = None,
        filename: str = "",
        content_type: str = "image/gif",
        file_type: FileType | str = FileType.ANIMATIONS,
        site_id: str | None = None,
        *,
        data: bytes | None = None,
    ) -> DeviceFile:
        """Upload a device asset file.

        Args:
            file_data: Raw file bytes (positional or keyword).
            filename: Name for the uploaded file.
            content_type: MIME type of the file.
            file_type: File type (animations or sounds).
            site_id: Optional site ID (unused in local API).
            data: Alias for file_data keyword argument.

        Returns:
            Created DeviceFile object.

        Raises:
            ValueError: If upload fails or file data is missing.

        """
        raw_bytes = file_data if file_data is not None else data
        if raw_bytes is None:
            raise ValueError("File data is required")

        ft = file_type.value if isinstance(file_type, FileType) else file_type
        path = self._client.build_api_path(f"/files/{ft}", site_id)

        def _build_form() -> aiohttp.FormData:
            form = aiohttp.FormData()
            form.add_field(
                "file",
                raw_bytes,
                filename=filename,
                content_type=content_type,
            )
            return form

        response = await self._client._request(
            "POST",
            path,
            body_factory=_build_form,
        )

        if response is None:
            raise ValueError(f"Failed to upload file {filename}")

        resp_data = (
            response.get("data", response)
            if isinstance(response, dict) and "data" in response
            else response
        )
        if not isinstance(resp_data, dict) or not resp_data:
            raise ValueError(f"Failed to upload file {filename}")
        return DeviceFile.model_validate(resp_data)

    async def trigger_alarm_webhook(
        self,
        trigger_id: str,
        site_id: str | None = None,
    ) -> bool:
        """Send a webhook to the Alarm Manager to trigger configured alarms.

        Args:
            trigger_id: User-defined trigger ID matching a configured alarm rule.
            site_id: Optional site ID (unused in local API).

        Returns:
            True if the webhook was accepted (204 No Content).

        Raises:
            ValueError: If trigger_id is empty.

        """
        if not trigger_id or not trigger_id.strip():
            raise ValueError("Trigger ID is required")

        path = self._client.build_api_path(f"/alarm-manager/webhook/{trigger_id}", site_id)
        await self._client._post(path)
        return True

    async def ingest_pos_transaction(
        self,
        camera_id: str,
        transaction: PosTransactionRequest | dict[str, Any],
        site_id: str | None = None,
    ) -> PosTransactionResponse:
        """Ingest a POS transaction on a camera via the POS endpoint."""
        return await self._client.pos.ingest_transaction(camera_id, transaction, site_id=site_id)
