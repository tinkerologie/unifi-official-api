"""Client for the UniFi Access developer API on the console's own port."""

from typing import TYPE_CHECKING, Any, Final

from yarl import URL

from ..base import BaseUniFiClient
from ..const import (
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_TIMEOUT,
)
from ..exceptions import (
    UniFiAuthenticationError,
    UniFiRateLimitError,
    UniFiResponseError,
    UniFiValidationError,
)
from .auth import AccessTokenAuth
from .endpoints import (
    DevicesEndpoint,
    DoorsEndpoint,
    EmergencyEndpoint,
    UsersEndpoint,
    WebhooksEndpoint,
)
from .errors import access_auth_error, envelope_error_code

if TYPE_CHECKING:
    import aiohttp

# The Access developer API is served by the console itself, on this port, with
# a self-signed certificate unless the user installs a trusted one.
ACCESS_API_PORT: Final = 12445
ACCESS_API_PATH: Final = "/api/v1/developer"
_MAX_PORT: Final = 65535


def _access_base_url(host: str, port: int) -> URL:
    """Return ``https://<host>:<port>/api/v1/developer`` for a host or URL."""
    text = host.strip()
    if "://" not in text:
        # A bare IPv6 literal needs brackets before a port can be appended.
        if text.count(":") > 1 and not text.startswith("["):
            text = f"[{text}]"
        text = f"https://{text}"
    parsed = URL(text)
    if parsed.host is None:
        msg = "Access host must include a host name or address"
        raise UniFiValidationError(msg)
    return URL.build(
        scheme="https",
        host=parsed.host,
        port=port,
        path=ACCESS_API_PATH,
    )


class UniFiAccessClient(BaseUniFiClient):
    """
    Async client for the UniFi Access developer API.

    Verified against the official Ubiquiti UniFi Access API Reference V2.2.10
    (``https://core-config-gfoz.uid.alpha.ui.com/configs/unifi-access/api_reference.pdf``,
    revision date ``2024-08-08``).

    Access is a separate application from Network and Protect. It uses its own
    bearer token and port, so it does not share the Network/Protect API key.
    Endpoint groups hang off the client:

    - ``doors``: list, read, unlock (optionally drive a gate) and lock rules
    - ``devices``: list hubs, readers and intercoms
    - ``emergency``: console-wide Lockdown and Evacuation
    - ``users``: PIN codes and account status
    - ``webhooks``: register signed endpoints
    """

    def __init__(
        self,
        *,
        token: str,
        host: str,
        port: int = ACCESS_API_PORT,
        verify_ssl: bool = True,
        session: aiohttp.ClientSession | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        connect_timeout: int = DEFAULT_CONNECT_TIMEOUT,
    ) -> None:
        """
        Initialize the Access client.

        Args:
            token: Access API token. Surrounding whitespace is removed.
            host: Console host name, IP address or ``https://`` URL.
            port: Developer API port, 12445 unless the console says otherwise.
            verify_ssl: Verify the console certificate on every request.
            session: Optional shared aiohttp client session.
            timeout: Request timeout in seconds.
            connect_timeout: Connection timeout in seconds.

        Raises:
            UniFiValidationError: If the token, host or port is unusable.

        """
        stripped = token.strip() if isinstance(token, str) else ""
        if not stripped:
            msg = "Access API token is required"
            raise UniFiValidationError(msg)
        if not isinstance(port, int) or not 1 <= port <= _MAX_PORT:
            msg = "Access port must be between 1 and 65535"
            raise UniFiValidationError(msg)

        self._verify_ssl = verify_ssl
        super().__init__(
            auth=AccessTokenAuth(token=stripped, verify_ssl=verify_ssl),
            base_url=str(_access_base_url(host, port)),
            session=session,
            timeout=timeout,
            connect_timeout=connect_timeout,
        )
        self.doors = DoorsEndpoint(self)
        self.devices = DevicesEndpoint(self)
        self.emergency = EmergencyEndpoint(self)
        self.users = UsersEndpoint(self)
        self.webhooks = WebhooksEndpoint(self)

    def _get_ssl_context(self) -> bool:
        """Return the verification setting for a connector this client creates."""
        return self._verify_ssl

    def _ssl_for_request(self) -> bool | None:
        """Apply verification per request, so a shared session honours it too."""
        return self._verify_ssl

    def _response_log_text(self, response_text: str, *, limit: int) -> str:
        """Keep Access response bodies out of logs: they can carry PINs and secrets."""
        return "[Access response omitted]"[:limit] if response_text else "empty"

    async def _handle_response(
        self,
        response: aiohttp.ClientResponse,
        *,
        expected_unsupported: bool = False,
        request_path: str | None = None,
        log_body: bool = True,
    ) -> dict[str, Any] | list[Any] | None:
        """
        Map Access error envelopes onto the library's exception types.

        The error ``code`` (for example ``CODE_RESOURCE_NOT_FOUND``) is kept on
        ``api_error_code``. The raw body is dropped from the exception, and the
        token-rejected message names the Access token rather than an API key.
        """
        try:
            return await super()._handle_response(
                response,
                expected_unsupported=expected_unsupported,
                request_path=request_path,
                log_body=log_body,
            )
        except UniFiAuthenticationError as err:
            raise access_auth_error(err.status_code, None) from None
        except UniFiRateLimitError as err:
            err.api_error_code = envelope_error_code(err.response_body)
            err.response_body = None
            raise
        except UniFiResponseError as err:
            err.api_error_code = envelope_error_code(err.response_body)
            err.response_body = None
            raise

    async def validate_connection(self) -> bool:
        """Validate the token by listing doors (``view:space``)."""
        await self.doors.get_all()
        return True
