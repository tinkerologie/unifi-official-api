"""Base async client for UniFi APIs."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import re
import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from http import HTTPStatus
from types import TracebackType
from typing import TYPE_CHECKING, Any, ClassVar, Final, Self, TypeVar

import aiohttp
from yarl import URL

from .auth import ApiKeyAuth, LocalAuth
from .const import (
    CONTENT_TYPE_JSON,
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_RATE_LIMIT_RETRY_AFTER,
    DEFAULT_TIMEOUT,
    HEADER_ACCEPT,
    HEADER_CONTENT_TYPE,
    HEADER_USER_AGENT,
    RATE_LIMIT_MAX_RETRY_AFTER,
    RATE_LIMIT_WINDOW_MARGIN,
    SENSITIVE_CREDENTIAL_KEYS,
    USER_AGENT,
)
from .exceptions import (
    UniFiAuthenticationError,
    UniFiConnectionError,
    UniFiNotFoundError,
    UniFiRateLimitError,
    UniFiResponseError,
    UniFiTimeoutError,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Mapping

    from .access.auth import AccessTokenAuth

_LOGGER = logging.getLogger(__name__)

_T = TypeVar("_T")

_TRANSPORT_ONLY_SENSITIVE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "apikey",
        "credential",
        "x-api-key",
        "authorization",
        "code",
        "pin",
        "pin_code",
        "pin_codes",
    }
)

_SENSITIVE_KEYS: Final[frozenset[str]] = frozenset(
    {k.lower() for k in SENSITIVE_CREDENTIAL_KEYS} | _TRANSPORT_ONLY_SENSITIVE_KEYS
)

_REDACTED_MALFORMED_BODY: Final[str] = "<malformed body redacted>"

# Group 1 keeps the key and separator. The value pattern consumes escaped
# quotes, so a secret containing a colon or an escaped quote is replaced whole.
_SENSITIVE_KEYS_PATTERN: Final[str] = "|".join(
    re.escape(k) for k in sorted(_SENSITIVE_KEYS, key=lambda k: (-len(k), k))
)
_SENSITIVE_KEYS_RE: Final[re.Pattern[str]] = re.compile(
    rf'("(?:{_SENSITIVE_KEYS_PATTERN})"\s*:\s*)'
    r'"(?:[^"\\]|\\[\s\S])*(?:"(?=\s*(?:[,}\]]|<|$))|\\?$)',
    re.IGNORECASE,
)
# Start at a quote to avoid rescanning unmatched backslash runs.
_UNSAFE_SENSITIVE_KEY_RE: Final[re.Pattern[str]] = re.compile(
    rf'["\'](?:{_SENSITIVE_KEYS_PATTERN})(?:\\*["\'])\s*:',
    re.IGNORECASE,
)
# Decode each backslash run once when checking escaped credential keys.
_UNICODE_ESCAPE_RE: Final[re.Pattern[str]] = re.compile(
    r"(?<!\\)\\+u([0-9a-fA-F]{4})",
    re.IGNORECASE,
)


def _redact_json(value: Any) -> Any:
    """Redact credential keys recursively regardless of their JSON value type."""
    if isinstance(value, dict):
        return {
            key: "**REDACTED**" if key.lower() in _SENSITIVE_KEYS else _redact_json(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_json(item) for item in value]
    return value


def _redact(text: str) -> str:
    """Redact parsed JSON credentials, or fail closed on unsafe non-JSON text."""
    try:
        value = json.loads(text)
    except ValueError:
        # Keep removed fragments apart while checking for unsafe key prefixes.
        remainder = _UNICODE_ESCAPE_RE.sub(
            lambda match: chr(int(match.group(1), 16)),
            _SENSITIVE_KEYS_RE.sub("\x00", text),
        )
        if _UNSAFE_SENSITIVE_KEY_RE.search(remainder):
            return _REDACTED_MALFORMED_BODY
        return _SENSITIVE_KEYS_RE.sub(r'\1"**REDACTED**"', text)
    return json.dumps(_redact_json(value))


def _retry_after_seconds(value: str | None) -> int:
    """Parse a Retry-After delay or HTTP date, with a safe fallback."""
    if not value:
        return DEFAULT_RATE_LIMIT_RETRY_AFTER
    try:
        seconds = float(value)
    except ValueError:
        try:
            deadline = parsedate_to_datetime(value)
        except TypeError, ValueError:
            return DEFAULT_RATE_LIMIT_RETRY_AFTER
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=UTC)
        seconds = (deadline - datetime.now(UTC)).total_seconds()
    if not math.isfinite(seconds):
        return DEFAULT_RATE_LIMIT_RETRY_AFTER
    return max(0, math.ceil(seconds))


def parse_retry_after(headers: Mapping[str, str]) -> int:
    """
    Return a 429 response's Retry-After in seconds.

    Parses integer/fractional seconds or HTTP dates (RFC 9110) and falls back
    to DEFAULT_RATE_LIMIT_RETRY_AFTER when the header is missing or invalid.
    """
    return _retry_after_seconds(headers.get("Retry-After"))


class RequestRateLimiter:
    """
    Space out requests so a client never exceeds a server-side rate limit.

    Allows at most `max_requests` request starts in any rolling `window`
    seconds. A rolling window is at least as strict as the server's fixed
    one, so staying inside it can never trip a fixed-window limit. Waiters
    are served in arrival order.
    """

    def __init__(self, max_requests: int, window: float) -> None:
        """Initialize the limiter."""
        self._max_requests = max_requests
        self._window = window
        self._starts: list[float] = []
        self._blocked_until = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until another request may start, then record it."""
        async with self._lock:
            while True:
                now = time.monotonic()
                cutoff = now - self._window
                self._starts = [t for t in self._starts if t > cutoff]
                if now < self._blocked_until:
                    wait = self._blocked_until - now
                elif len(self._starts) < self._max_requests:
                    self._starts.append(now)
                    return
                else:
                    wait = self._starts[0] - cutoff
                await asyncio.sleep(wait)

    def defer(self, seconds: float) -> None:
        """Hold every request for `seconds`, e.g. after a server 429."""
        self._blocked_until = max(self._blocked_until, time.monotonic() + seconds)


class BaseUniFiClient(ABC):
    """
    Base async client for UniFi API interactions.

    This class provides common functionality across all UniFi API clients.
    """

    # (max requests, window seconds) the server enforces, or None if the
    # API is not rate limited. Subclasses set this; see `_throttle`.
    RATE_LIMIT: ClassVar[tuple[int, float] | None] = None

    def __init__(
        self,
        auth: ApiKeyAuth | LocalAuth | AccessTokenAuth,
        base_url: str,
        *,
        session: aiohttp.ClientSession | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        connect_timeout: int = DEFAULT_CONNECT_TIMEOUT,
    ) -> None:
        """
        Initialize the base client.

        Args:
            auth: Authentication configuration.
            base_url: Base URL for the API.
            session: Optional aiohttp session to reuse.
            timeout: Request timeout in seconds.
            connect_timeout: Connection timeout in seconds.

        """
        self._auth = auth
        self._base_url = URL(base_url)
        self._session = session
        self._owns_session = session is None
        self._timeout = aiohttp.ClientTimeout(
            total=timeout,
            connect=connect_timeout,
        )
        self._closed = False
        self._rate_limiter: RequestRateLimiter | None = None
        if self.RATE_LIMIT is not None:
            max_requests, window = self.RATE_LIMIT
            self._rate_limiter = RequestRateLimiter(max_requests, window + RATE_LIMIT_WINDOW_MARGIN)

    @property
    def base_url(self) -> URL:
        """Return the base URL."""
        return self._base_url

    @property
    def closed(self) -> bool:
        """Return whether the client is closed."""
        return self._closed

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """
        Ensure an aiohttp session exists.

        Returns:
            The aiohttp session.

        """
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                ssl=self._get_ssl_context(),
            )
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=self._timeout,
            )
            self._owns_session = True
        return self._session

    def _get_ssl_context(self) -> bool:
        """
        Get SSL context based on auth configuration.

        Returns:
            SSL verification setting.

        """
        if isinstance(self._auth, LocalAuth):
            return self._auth.verify_ssl
        return True

    def _ssl_for_request(self) -> bool | None:
        """
        Return a per-request TLS verification override, or None for the session's.

        A shared caller session keeps its own connector, so a client that
        verifies differently passes its setting on every request.
        """
        return None

    def _get_headers(self) -> dict[str, str]:
        """
        Get default headers for requests.

        Returns:
            Dictionary of headers.

        """
        headers = {
            HEADER_USER_AGENT: USER_AGENT,
            HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON,
            HEADER_ACCEPT: CONTENT_TYPE_JSON,
        }
        headers.update(self._auth.get_headers())
        return headers

    def _build_url(self, path: str) -> URL:
        """
        Build full URL from path.

        Args:
            path: API path (should start with /).

        Returns:
            Full URL.

        """
        return self._base_url / path.lstrip("/")

    async def _throttle(self) -> None:
        """Wait for the client's rate limiter, if the API has one."""
        if self._rate_limiter is not None:
            await self._rate_limiter.acquire()

    def _defer_after_rate_limit(self, retry_after: float | None) -> None:
        """
        Hold all of this client's requests after the server sent a 429.

        Capped at RATE_LIMIT_MAX_RETRY_AFTER: a missing Retry-After defaults
        to a minute, which must not freeze every request on the client.
        """
        if self._rate_limiter is not None:
            if retry_after is None:
                retry_after = RATE_LIMIT_MAX_RETRY_AFTER
            self._rate_limiter.defer(min(retry_after, RATE_LIMIT_MAX_RETRY_AFTER))

    async def _retry_once_after_rate_limit(
        self,
        send: Callable[[], Awaitable[_T]],
        description: str,
    ) -> _T:
        """
        Run `send`, retrying it once after a short-lived 429.

        Rate-limited APIs are paced by `_throttle`, so a 429 means another
        consumer of the same API key drained the allowance. A rejected
        request was not processed, so retrying it once after the server's
        own Retry-After is safe for every method. Every 429, including one
        on the retry, holds the client's other requests for the (capped)
        Retry-After, so they do not run into the allowance the server has
        just refused. A long or missing Retry-After is raised to the caller
        without a retry.

        Raises:
            UniFiRateLimitError: If still rate limited after the retry, or the
                server asks for a wait longer than RATE_LIMIT_MAX_RETRY_AFTER.

        """
        if self._rate_limiter is None:
            return await send()
        try:
            return await send()
        except UniFiRateLimitError as err:
            retry_after = err.retry_after
            self._defer_after_rate_limit(retry_after)
            if retry_after is None or retry_after > RATE_LIMIT_MAX_RETRY_AFTER:
                raise
            _LOGGER.debug("Rate limited on %s, retrying in %ss", description, retry_after)
        try:
            return await send()
        except UniFiRateLimitError as err:
            self._defer_after_rate_limit(err.retry_after)
            raise

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        body_factory: Callable[[], aiohttp.FormData] | None = None,
        headers: dict[str, str] | None = None,
        expected_unsupported: bool = False,
        log_body: bool = True,
    ) -> dict[str, Any] | list[Any] | None:
        """
        Make an HTTP request, retrying once after a short-lived 429.

        See `_retry_once_after_rate_limit`.

        Raises:
            UniFiRateLimitError: If still rate limited after the retry, or the
                server asks for a wait longer than RATE_LIMIT_MAX_RETRY_AFTER.

        """
        return await self._retry_once_after_rate_limit(
            lambda: self._request_once(
                method,
                path,
                params=params,
                json_data=json_data,
                body_factory=body_factory,
                headers=headers,
                expected_unsupported=expected_unsupported,
                log_body=log_body,
            ),
            f"{method} {path}",
        )

    async def _request_once(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        body_factory: Callable[[], aiohttp.FormData] | None = None,
        headers: dict[str, str] | None = None,
        expected_unsupported: bool = False,
        log_body: bool = True,
    ) -> dict[str, Any] | list[Any] | None:
        """
        Make a single HTTP request to the API.

        Args:
            method: HTTP method.
            path: API path.
            params: Query parameters.
            json_data: JSON body data.
            body_factory: Build a fresh multipart body for this attempt
                (omits all Content-Type headers).
            headers: Additional headers.
            expected_unsupported: Whether a non-JSON 2xx response is an
                expected unsupported-endpoint signal.
            log_body: Whether redacted response body excerpts may be logged.

        Returns:
            Response data as dict, list, or None.

        Raises:
            UniFiAuthenticationError: If authentication fails.
            UniFiConnectionError: If connection fails.
            UniFiNotFoundError: If resource not found.
            UniFiRateLimitError: If rate limited.
            UniFiResponseError: If API returns an error.
            UniFiTimeoutError: If request times out.

        """
        await self._throttle()
        session = await self._ensure_session()
        url = self._build_url(path)

        request_headers = self._get_headers()
        if headers:
            request_headers.update(headers)
        if body_factory is not None:
            # Omit all Content-Type headers in any casing, letting aiohttp supply
            # the multipart boundary while retaining authentication and other
            # caller header overrides.
            request_headers = {
                key: value
                for key, value in request_headers.items()
                if key.lower() != HEADER_CONTENT_TYPE.lower()
            }

        _LOGGER.debug(
            "Making %s request to %s",
            method,
            url,
        )

        request_options: dict[str, Any] = {}
        ssl = self._ssl_for_request()
        if ssl is not None:
            request_options["ssl"] = ssl

        try:
            request_body: dict[str, Any] = (
                {"data": body_factory()} if body_factory is not None else {"json": json_data}
            )
            async with session.request(
                method,
                url,
                params=params,
                **request_body,
                headers=request_headers,
                **request_options,
            ) as response:
                return await self._handle_response(
                    response,
                    expected_unsupported=expected_unsupported,
                    request_path=path,
                    log_body=log_body,
                )

        except aiohttp.ClientConnectorError as err:
            msg = f"Failed to connect to {url}: {err}"
            raise UniFiConnectionError(msg) from err
        except TimeoutError as err:
            msg = f"Request to {url} timed out"
            raise UniFiTimeoutError(msg) from err
        except aiohttp.ClientError as err:
            msg = f"Request to {url} failed: {err}"
            raise UniFiConnectionError(msg) from err

    def _response_log_text(self, response_text: str, *, limit: int) -> str:
        """Return a bounded, credential-redacted response excerpt for logs."""
        return _redact(response_text)[:limit] if response_text else "empty"

    async def _handle_response(
        self,
        response: aiohttp.ClientResponse,
        *,
        expected_unsupported: bool = False,
        request_path: str | None = None,
        log_body: bool = True,
    ) -> dict[str, Any] | list[Any] | None:
        """
        Handle API response.

        Args:
            response: The aiohttp response.
            expected_unsupported: Log unredirected non-JSON 2xx responses at
                DEBUG as expected unsupported-endpoint signals.
            request_path: Original request path before any redirect.
            log_body: Whether redacted response body excerpts may be logged.

        Returns:
            Response data.

        Raises:
            UniFiAuthenticationError: If authentication fails.
            UniFiNotFoundError: If resource not found.
            UniFiRateLimitError: If rate limited.
            UniFiResponseError: If API returns an error.

        """
        status = response.status
        response_text = await response.text()

        if _LOGGER.isEnabledFor(logging.DEBUG):
            # Retain the override used by clients that omit response bodies.
            redacted_body = (
                self._response_log_text(response_text, limit=500)
                if log_body
                else f"<body omitted, {len(response_text.encode('utf-8'))} bytes>"
            )
            _LOGGER.debug(
                "Response status: %s, body: %s",
                status,
                redacted_body,
            )

        if status == HTTPStatus.UNAUTHORIZED:
            raise UniFiAuthenticationError(
                "Authentication failed. Check your API key.", status_code=status
            )

        if status == HTTPStatus.FORBIDDEN:
            raise UniFiAuthenticationError(
                "Access forbidden. Check your API key permissions.",
                status_code=status,
            )

        if status == HTTPStatus.NOT_FOUND:
            raise UniFiNotFoundError(
                "Resource not found",
                status_code=status,
                response_body=response_text,
            )

        if status == HTTPStatus.TOO_MANY_REQUESTS:
            raise UniFiRateLimitError(
                "Rate limited by API",
                status_code=status,
                response_body=response_text,
                retry_after=parse_retry_after(response.headers),
            )

        if status >= HTTPStatus.BAD_REQUEST:
            message = f"API error (status {status})"
            raise UniFiResponseError(
                message,
                status_code=status,
                response_body=response_text,
            )

        if not response_text:
            return None

        try:
            data: dict[str, Any] | list[Any] = await response.json()
            return data
        except (ValueError, aiohttp.ContentTypeError) as err:
            # A 2xx status with a non-JSON body (e.g. an HTML login page from
            # a proxy/console that considers the request unauthenticated) is
            # not a successful empty response.
            redacted_response = (
                self._response_log_text(response_text, limit=200)
                if log_body
                else f"<body omitted, {len(response_text.encode('utf-8'))} bytes>"
            )
            expected_path = (
                self._build_url(request_path).path
                if request_path is not None
                else response.url.path
            )
            history = getattr(response, "history", ())
            is_unredirected = isinstance(history, (tuple, list)) and len(history) == 0
            if expected_unsupported and is_unredirected and response.url.path == expected_path:
                _LOGGER.debug(
                    "Expected unsupported-endpoint non-JSON response for %s %s: %s",
                    response.method,
                    response.url.path,
                    redacted_response,
                )
            else:
                # Log the request path: without it this warning names only the
                # body, so a console returning an HTML page on one of several
                # polled endpoints cannot be attributed to the endpoint that
                # actually failed. `url.path` deliberately omits the query
                # string, which can carry credentials.
                _LOGGER.warning(
                    "Response is not JSON for %s %s: %s",
                    response.method,
                    response.url.path,
                    redacted_response,
                )
            msg = f"API returned non-JSON response (status {status})"
            raise UniFiResponseError(
                msg,
                status_code=status,
                response_body=response_text,
            ) from err

    async def _get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        expected_unsupported: bool = False,
        log_body: bool = True,
    ) -> dict[str, Any] | list[Any] | None:
        """
        Make a GET request.

        Args:
            path: API path.
            params: Query parameters.
            expected_unsupported: Whether a non-JSON 2xx response is an
                expected unsupported-endpoint signal.
            log_body: Whether redacted response body excerpts may be logged.

        Returns:
            Response data.

        """
        return await self._request(
            "GET",
            path,
            params=params,
            expected_unsupported=expected_unsupported,
            log_body=log_body,
        )

    async def _post(
        self,
        path: str,
        *,
        json_data: dict[str, Any] | None = None,
        body_factory: Callable[[], aiohttp.FormData] | None = None,
        params: dict[str, Any] | None = None,
        expected_unsupported: bool = False,
        log_body: bool = True,
    ) -> dict[str, Any] | list[Any] | None:
        """
        Make a POST request.

        Args:
            path: API path.
            json_data: JSON body data.
            body_factory: Build a fresh multipart body for each attempt
                (omits all Content-Type headers).
            params: Query parameters.
            expected_unsupported: Whether a non-JSON 2xx response is an
                expected unsupported-endpoint signal.
            log_body: Whether redacted response body excerpts may be logged.

        Returns:
            Response data.

        """
        return await self._request(
            "POST",
            path,
            json_data=json_data,
            body_factory=body_factory,
            params=params,
            expected_unsupported=expected_unsupported,
            log_body=log_body,
        )

    async def _put(
        self,
        path: str,
        *,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        log_body: bool = True,
    ) -> dict[str, Any] | list[Any] | None:
        """
        Make a PUT request.

        Args:
            path: API path.
            json_data: JSON body data.
            params: Query parameters.
            log_body: Whether redacted response body excerpts may be logged.

        Returns:
            Response data.

        """
        return await self._request(
            "PUT", path, json_data=json_data, params=params, log_body=log_body
        )

    async def _patch(
        self,
        path: str,
        *,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        log_body: bool = True,
    ) -> dict[str, Any] | list[Any] | None:
        """
        Make a PATCH request.

        Args:
            path: API path.
            json_data: JSON body data.
            params: Query parameters.
            log_body: Whether redacted response body excerpts may be logged.

        Returns:
            Response data.

        """
        return await self._request(
            "PATCH", path, json_data=json_data, params=params, log_body=log_body
        )

    async def _delete(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        log_body: bool = True,
    ) -> dict[str, Any] | list[Any] | None:
        """
        Make a DELETE request.

        Args:
            path: API path.
            params: Query parameters.
            json_data: JSON body data.
            log_body: Whether redacted response body excerpts may be logged.

        Returns:
            Response data.

        """
        return await self._request(
            "DELETE", path, params=params, json_data=json_data, log_body=log_body
        )

    async def _get_binary_with_content_type(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> tuple[bytes, str]:
        """
        Make a GET request that returns binary data and its content type.

        Args:
            path: API path.
            params: Query parameters.

        Returns:
            Tuple of (binary_content, content_type).

        A 429 is waited out and retried once, like the JSON requests: see
        `_retry_once_after_rate_limit`.

        Raises:
            UniFiAuthenticationError: If authentication fails.
            UniFiConnectionError: If connection fails.
            UniFiNotFoundError: If resource not found.
            UniFiRateLimitError: If rate limited.
            UniFiResponseError: If API returns an error.
            UniFiTimeoutError: If request times out.

        """
        return await self._retry_once_after_rate_limit(
            lambda: self._get_binary_once(path, params=params),
            f"GET {path}",
        )

    async def _get_binary_once(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> tuple[bytes, str]:
        """
        Make a single binary GET request.

        Raises:
            UniFiAuthenticationError: If authentication fails.
            UniFiConnectionError: If connection fails.
            UniFiNotFoundError: If resource not found.
            UniFiRateLimitError: If rate limited.
            UniFiResponseError: If API returns an error.
            UniFiTimeoutError: If request times out.

        """
        await self._throttle()
        session = await self._ensure_session()
        url = self._build_url(path)
        headers = self._get_headers()
        # Remove JSON content type for binary requests
        headers.pop(HEADER_CONTENT_TYPE, None)
        headers[HEADER_ACCEPT] = "*/*"

        _LOGGER.debug(
            "Making binary GET request to %s",
            url,
        )

        request_options: dict[str, Any] = {}
        ssl = self._ssl_for_request()
        if ssl is not None:
            request_options["ssl"] = ssl

        try:
            async with session.get(
                url,
                params=params,
                headers=headers,
                **request_options,
            ) as response:
                status = response.status
                if status >= HTTPStatus.BAD_REQUEST:
                    text = await response.text()
                    if status == HTTPStatus.UNAUTHORIZED:
                        msg = "Authentication failed. Check your API key."
                        raise UniFiAuthenticationError(msg, status_code=status)
                    if status == HTTPStatus.FORBIDDEN:
                        msg = "Access forbidden. Check your API key permissions."
                        raise UniFiAuthenticationError(msg, status_code=status)
                    if status == HTTPStatus.NOT_FOUND:
                        msg = "Resource not found"
                        raise UniFiNotFoundError(
                            msg,
                            status_code=status,
                            response_body=text,
                        )
                    if status == HTTPStatus.TOO_MANY_REQUESTS:
                        msg = "Rate limited by API"
                        raise UniFiRateLimitError(
                            msg,
                            status_code=status,
                            response_body=text,
                            retry_after=parse_retry_after(response.headers),
                        )
                    msg = f"API error (status {status})"
                    raise UniFiResponseError(
                        msg,
                        status_code=status,
                        response_body=text,
                    )

                data = await response.read()
                content_type = response.content_type or response.headers.get(
                    HEADER_CONTENT_TYPE, "application/octet-stream"
                )
                return data, content_type

        except aiohttp.ClientConnectorError as err:
            msg = f"Failed to connect to {url}: {err}"
            raise UniFiConnectionError(msg) from err
        except TimeoutError as err:
            msg = f"Request to {url} timed out"
            raise UniFiTimeoutError(msg) from err
        except aiohttp.ClientError as err:
            msg = f"Request to {url} failed: {err}"
            raise UniFiConnectionError(msg) from err

    @abstractmethod
    async def validate_connection(self) -> bool:
        """
        Validate the connection to the API.

        Returns:
            True if connection is valid.

        """

    async def close(self) -> None:
        """Close the client session."""
        if self._session and self._owns_session and not self._session.closed:
            await self._session.close()
        self._closed = True

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager."""
        await self.close()
