"""Parsing and per-request outcomes for best-effort Protect listings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from pydantic import BaseModel, ValidationError

from ...validation import sanitized_validation_fields

if TYPE_CHECKING:
    import logging


@dataclass(frozen=True, slots=True)
class ProtectListResult[ModelT: BaseModel]:
    """Parsed records and completeness evidence from one Protect request.

    An empty list is complete when the response had a list shape. A missing or
    invalid list shape and rejected records make the result incomplete.
    Transport failures still raise through the endpoint.
    """

    records: tuple[ModelT, ...]
    skipped: int
    shape_valid: bool

    @property
    def complete(self) -> bool:
        """Return whether the response provides a complete listing."""
        return self.shape_valid and self.skipped == 0


class _ListingState(Protocol):
    last_result_complete: bool


def listing_items(response: object) -> list[Any] | None:
    """Extract a bare or data-wrapped list, keeping invalid shapes distinct."""
    data = response.get("data", response) if isinstance(response, dict) else response
    return data if isinstance(data, list) else None


def parse_listing[ModelT: BaseModel](
    model: type[ModelT],
    response: object,
    resource: str,
    logger: logging.Logger,
    *,
    legacy_state: _ListingState | None = None,
) -> ProtectListResult[ModelT]:
    """Parse one listing with schema-only diagnostics for rejected records."""
    items = listing_items(response)
    if items is None:
        return ProtectListResult(records=(), skipped=0, shape_valid=False)

    records: list[ModelT] = []
    skipped = 0
    for index, item in enumerate(items):
        try:
            records.append(model.model_validate(item))
        except ValidationError as err:
            skipped += 1
            if legacy_state is not None:
                legacy_state.last_result_complete = False
            logger.warning(
                "Skipping %s at index %d that failed validation (fields: %s)",
                resource,
                index,
                sanitized_validation_fields(err, model=model),
            )
    return ProtectListResult(records=tuple(records), skipped=skipped, shape_valid=True)
