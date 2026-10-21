"""Point of sale (POS) endpoint for UniFi Protect API."""

from typing import TYPE_CHECKING, Any

from ..models.pos import (
    POSTransactionRequest,
    PosTransactionRequest,
    PosTransactionResponse,
)

if TYPE_CHECKING:
    from ..client import UniFiProtectClient


class POSEndpoint:
    """Endpoint for UniFi Protect point of sale (POS) transaction ingestion."""

    def __init__(self, client: UniFiProtectClient) -> None:
        """Initialize the POS endpoint."""
        self._client = client

    async def ingest_transaction(
        self,
        camera_id: str,
        transaction: PosTransactionRequest | POSTransactionRequest | dict[str, Any],
        site_id: str | None = None,
    ) -> PosTransactionResponse:
        """
        Ingest a POS transaction to overlay on camera footage.

        Args:
            camera_id: Target camera ID.
            transaction: Transaction request model or payload dict.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The POS transaction ingestion response.

        Raises:
            ValueError: If the camera ID is invalid or response cannot be parsed.
            TypeError: If the transaction is not a PosTransactionRequest or dict.
        """
        if not isinstance(camera_id, str) or not camera_id.strip():
            msg = "Camera ID must be a non-empty string"
            raise ValueError(msg)

        path = self._client.build_api_path(f"/pos/cameras/{camera_id}/transactions", site_id)
        if isinstance(transaction, (PosTransactionRequest, POSTransactionRequest)):
            payload = transaction.model_dump(by_alias=True, exclude_none=True)
        elif isinstance(transaction, dict):
            payload = PosTransactionRequest.model_validate(transaction).model_dump(
                by_alias=True, exclude_none=True
            )
        else:
            msg = (
                "Transaction must be a PosTransactionRequest or dict, "
                f"got {type(transaction).__name__}"
            )
            raise TypeError(msg)

        response = await self._client._post(path, json_data=payload)

        if isinstance(response, dict):
            data = response.get("data", response)
            if isinstance(data, dict):
                return PosTransactionResponse.model_validate(data)
        msg = f"Failed to ingest POS transaction for camera {camera_id}"
        raise ValueError(msg)


PosEndpoint = POSEndpoint

__all__ = ["POSEndpoint", "PosEndpoint"]
