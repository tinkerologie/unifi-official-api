"""Error mapping for the UniFi Access developer API."""

from __future__ import annotations

import json
import re
from http import HTTPStatus
from typing import Any

from ..exceptions import (
    UniFiAuthenticationError,
    UniFiNotFoundError,
    UniFiResponseError,
)

# Documented Access error codes are upper-case ``CODE_*`` identifiers. Anything
# else in a response is treated as untrusted and dropped, so an arbitrary string
# in a response body can never reach an exception attribute or a log.
_CODE_PATTERN = re.compile(r"CODE_[A-Z0-9_]{1,60}")

# Documented codes that mean the token is rejected (401) or not allowed (403),
# as opposed to a missing resource. The HTTP status is kept so callers see the
# same classes whether the console answers with a status code or with an
# HTTP 200 error envelope.
_AUTH_STATUS_BY_CODE: dict[str, int] = {
    "CODE_AUTH_FAILED": 401,
    "CODE_ACCESS_TOKEN_INVALID": 401,
    "CODE_UNAUTHORIZED": 403,
    "CODE_OPERATION_FORBIDDEN": 403,
}

# Documented codes for a resource that does not exist, including an unknown
# user. These are raised as UniFiNotFoundError, which callers treat as an
# unknown target rather than an API outage.
_NOT_FOUND_CODES = frozenset(
    {
        "CODE_RESOURCE_NOT_FOUND",
        "CODE_NOT_EXISTS",
        "CODE_USER_WORKER_NOT_EXISTS",
        "CODE_USER_ACCOUNT_NOT_EXIST",
        "CODE_DEVICE_DEVICE_NOT_FOUND",
    }
)

_AUTH_REJECTED_MESSAGE = "Access token rejected. Check the Access API token."
_PERMISSION_DENIED = "Access token lacks permission for this action."
_NOT_FOUND = "Access resource not found"


def safe_code(code: object) -> str | None:
    """Return a documented-shape ``CODE_*`` identifier, or None for anything else."""
    if isinstance(code, str) and _CODE_PATTERN.fullmatch(code):
        return code
    return None


def access_response_error(path: str, detail: str) -> UniFiResponseError:
    """Return a response error for a successful but malformed Access payload."""
    return UniFiResponseError(f"{path} returned a {detail}", status_code=200)


def access_auth_error(
    status_code: int | None, api_error_code: str | None
) -> UniFiAuthenticationError:
    """Return the authentication error for a 401 or 403, with no server text."""
    message = (
        _AUTH_REJECTED_MESSAGE if status_code == HTTPStatus.UNAUTHORIZED else _PERMISSION_DENIED
    )
    return UniFiAuthenticationError(
        message,
        status_code=status_code,
        api_error_code=api_error_code,
    )


def access_code_error(
    path: str, code: object
) -> UniFiAuthenticationError | UniFiNotFoundError | UniFiResponseError:
    """
    Map a documented error code from an HTTP 200 envelope to an exception.

    Authentication and permission codes become ``UniFiAuthenticationError`` with
    the matching 401 or 403 status. Missing-resource codes become
    ``UniFiNotFoundError`` (404). Any other code stays a ``UniFiResponseError``
    with status 200, which is how the envelope arrived. The server ``msg`` is
    never used.
    """
    checked = safe_code(code)
    if checked in _AUTH_STATUS_BY_CODE:
        return access_auth_error(_AUTH_STATUS_BY_CODE[checked], checked)
    if checked in _NOT_FOUND_CODES:
        return UniFiNotFoundError(
            _NOT_FOUND,
            status_code=404,
            api_error_code=checked,
        )
    return UniFiResponseError(
        f"{path} returned an Access error",
        status_code=200,
        api_error_code=checked,
    )


def ensure_success_envelope(response: Any, path: str) -> dict[str, Any]:
    """
    Require a ``{"code": "SUCCESS", ...}`` envelope, for reads and writes alike.

    The console can answer HTTP 200 with an error code in the body, so HTTP
    status alone never proves success. A missing body is also a failure: the
    documented success response always carries the envelope.
    """
    if not isinstance(response, dict):
        raise access_response_error(path, "malformed response envelope")
    if response.get("code") != "SUCCESS":
        raise access_code_error(path, response.get("code"))
    return response


def envelope_error_code(response_body: str | None) -> str | None:
    """
    Return the documented ``code`` of an Access error envelope, or None.

    Only the short code is kept. The ``msg`` text and the rest of the body are
    dropped, so nothing from a response reaches logs or user-facing messages.
    """
    if not response_body:
        return None
    try:
        envelope = json.loads(response_body)
    except ValueError:
        return None
    if not isinstance(envelope, dict):
        return None
    return safe_code(envelope.get("code"))
