# Copyright (c) 2026 Ruaan Deysel
"""Validation error helpers for API response handling."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, ValidationError

from .exceptions import UniFiNotFoundError, UniFiResponseError


def sanitized_validation_fields(err: ValidationError) -> str:
    """Return sorted, de-duplicated validation field names without values."""
    field_names = [str((item.get("loc") or ("root",))[-1]) for item in err.errors()]
    return ", ".join(sorted(set(field_names)))


def response_record(response: object, *, id_key: str | None = "id") -> dict[str, Any] | None:
    """
    Return the single record in a response, or None when it holds none.

    The record may be the body itself or sit under a ``data`` key, and either
    may be a list whose first item is the record. With ``id_key`` set, a record
    without a value under that key does not count.
    """
    if isinstance(response, list):
        data: Any = response
    elif isinstance(response, dict):
        data = response.get("data", response)
    else:
        return None
    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict) or not data:
        return None
    if id_key is not None and not data.get(id_key):
        return None
    return data


def parse_record[ModelT: BaseModel](model: type[ModelT], record: object, what: str) -> ModelT:
    """
    Validate one response record, or raise a sanitized response error.

    The pydantic ``ValidationError`` quotes the rejected input, so it is caught
    and the response error is raised after the ``except`` block: the message
    names fields only, and neither ``__cause__`` nor ``__context__`` points at
    the input.

    Raises:
        UniFiResponseError: With status 200, if the record fails validation.

    """
    try:
        return model.model_validate(record)
    except ValidationError as err:
        fields = sanitized_validation_fields(err)
    raise UniFiResponseError(f"{what} response failed validation ({fields})", status_code=200)


def parse_records[ModelT: BaseModel](
    model: type[ModelT], items: Iterable[object], what: str
) -> list[ModelT]:
    """
    Validate every record of a list response, or raise a sanitized response error.

    For listings that cannot report a skipped record: dropping one silently
    would make a record the console returned look absent, so the first record
    that fails validation fails the read.

    Raises:
        UniFiResponseError: With status 200, if any record fails validation.

    """
    return [parse_record(model, item, what) for item in items]


def require_record[ModelT: BaseModel](
    response: object,
    model: type[ModelT],
    what: str,
    *,
    id_key: str | None = "id",
) -> ModelT:
    """
    Parse the single record of a successful read.

    Raises:
        UniFiNotFoundError: With status 200, if the response holds no record.
        UniFiResponseError: With status 200, if the record fails validation.

    """
    record = response_record(response, id_key=id_key)
    if record is None:
        raise UniFiNotFoundError(f"{what} not found", status_code=200)
    return parse_record(model, record, what)


def created_record[ModelT: BaseModel](
    response: object,
    model: type[ModelT],
    what: str,
    *,
    id_key: str | None = "id",
) -> ModelT:
    """
    Parse the record a successful create returned.

    Unlike an update, a create whose response does not hold the new record
    cannot fall back to a re-fetch: without its ID the record cannot be looked
    up, so the response is reported as malformed.

    Raises:
        UniFiResponseError: With status 200, if the response holds no valid
            record. The resource may still have been created.

    """
    record = response_record(response, id_key=id_key)
    if record is None:
        msg = f"{what} create response holds no record; it may have been created"
        raise UniFiResponseError(msg, status_code=200)
    return parse_record(model, record, what)


def written_record[ModelT: BaseModel](
    response: object,
    model: type[ModelT],
    *,
    id_key: str | None = "id",
) -> ModelT | None:
    """
    Parse the record a successful write echoed back, or None when it holds none.

    A console may acknowledge a write with an empty or partial body. The write
    has still been applied, so the caller re-fetches instead of failing.
    """
    record = response_record(response, id_key=id_key)
    if record is None:
        return None
    try:
        return model.model_validate(record)
    except ValidationError:
        return None
