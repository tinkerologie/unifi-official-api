"""Point of Sale (POS) transaction models for UniFi Protect API."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class PosTransactionType(StrEnum):
    """Types of POS transactions."""

    SALE = "sale"
    RETURN = "return"
    REFUND = "refund"
    VOID = "void"
    EXCHANGE = "exchange"
    NO_SALE = "no_sale"
    PAID_IN = "paid_in"
    PAID_OUT = "paid_out"
    DISCOUNT = "discount"
    OTHER = "other"


class PosLineItem(BaseModel):
    """Individual line item in a POS transaction."""

    title: str = Field(..., description="Item description")
    quantity: int | float = Field(..., description="Item quantity")

    model_config = {"populate_by_name": True, "extra": "forbid"}


class PosLocation(BaseModel):
    """POS terminal or register location."""

    id: str = Field(..., description="Terminal or register identifier")
    name: str | None = Field(default=None, description="Human-readable terminal name")

    model_config = {"populate_by_name": True, "extra": "forbid"}


class PosTransactionRequest(BaseModel):
    """Request payload for ingesting a POS transaction on a camera."""

    type: PosTransactionType = Field(..., description="Transaction type")
    external_id: str = Field(
        ...,
        alias="externalId",
        description="External transaction ID for idempotency",
    )
    amount: float = Field(..., description="Total transaction amount")
    currency: str | None = Field(
        default=None,
        description="ISO 4217 3-letter currency code (defaults to USD on server)",
    )
    line_items: list[PosLineItem] | None = Field(
        default=None,
        alias="lineItems",
        description="Individual line items (max 50)",
    )
    location: PosLocation | None = Field(
        default=None, description="POS terminal or register location"
    )
    payment_types: list[str] | None = Field(
        default=None,
        alias="paymentTypes",
        description="Payment methods used (max 10)",
    )
    timestamp: int | None = Field(
        default=None,
        description="Transaction timestamp in Unix milliseconds",
    )

    model_config = {"populate_by_name": True, "extra": "forbid"}


class PosTransactionResponse(BaseModel):
    """Response returned when ingesting a POS transaction."""

    created: bool = Field(
        ...,
        description="True if newly created; False if matched existing externalId",
    )
    event_id: str = Field(..., alias="eventId", description="Protect POS event identifier")

    model_config = {"populate_by_name": True, "extra": "allow"}


POSLineItem = PosLineItem
POSLocation = PosLocation
POSTransactionRequest = PosTransactionRequest
POSTransactionResponse = PosTransactionResponse
POSTransactionType = PosTransactionType
