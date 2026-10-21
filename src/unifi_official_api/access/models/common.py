"""Shared parsing helpers for UniFi Access payloads."""

from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from ..errors import access_response_error, ensure_success_envelope


class AccessRecord(BaseModel):
    """Base model: unknown fields are ignored, never rejected."""

    model_config = ConfigDict(extra="ignore", frozen=True)


def known_or_none[EnumT: str](value: Any, allowed: tuple[EnumT, ...]) -> EnumT | None:
    """Return the value when it is a documented enum member, otherwise None."""
    if isinstance(value, str) and value in allowed:
        return value
    return None


def validate_record[ModelT: AccessRecord](
    model: type[ModelT],
    value: dict[str, Any],
    path: str,
) -> ModelT:
    """
    Validate one record, or raise a sanitized response error.

    A pydantic ``ValidationError`` quotes the rejected input, and that input can
    be a signing secret. It is caught here and never chained, stored or
    formatted. The response error is raised after the ``except`` block, so no
    ``__context__`` or ``__cause__`` points at the input.
    """
    try:
        return model.model_validate(value)
    except ValidationError:
        pass
    raise access_response_error(path, "malformed record")


def parse_records[ModelT: AccessRecord](
    response: dict[str, Any] | list[Any] | None,
    model: type[ModelT],
    path: str,
) -> list[ModelT]:
    """
    Parse a ``{"code", "data": [...]}`` list envelope into models.

    The console returns device records nested one level deeper than the
    documented schema in some firmware, so a list item that is itself a list
    is flattened.
    """
    data = ensure_success_envelope(response, path).get("data")
    if not isinstance(data, list):
        raise access_response_error(path, "malformed data")
    records: list[ModelT] = []
    for item in data:
        group = item if isinstance(item, list) else [item]
        for record in group:
            if not isinstance(record, dict):
                raise access_response_error(path, "malformed record")
            records.append(validate_record(model, record, path))
    return records


def parse_record[ModelT: AccessRecord](
    response: dict[str, Any] | list[Any] | None,
    model: type[ModelT],
    path: str,
) -> ModelT:
    """
    Parse a single-object ``data`` envelope into a model.

    Some endpoints wrap their single object in a one-item list, so both forms
    are accepted.
    """
    data = ensure_success_envelope(response, path).get("data")
    if isinstance(data, list) and len(data) == 1:
        data = data[0]
    if not isinstance(data, dict):
        raise access_response_error(path, "malformed data")
    return validate_record(model, data, path)
