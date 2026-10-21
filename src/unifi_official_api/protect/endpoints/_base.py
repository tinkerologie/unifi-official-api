"""Shared base for simple UniFi Protect device-family endpoints."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError

from ...exceptions import UniFiNotFoundError, UniFiResponseError
from ...validation import sanitized_validation_fields

if TYPE_CHECKING:
    from ..client import UniFiProtectClient

_LOGGER = logging.getLogger(__name__)

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class ProtectDeviceEndpoint(Generic[_ModelT]):
    """
    Base endpoint providing standard ``get_all``/``get``/``update`` behaviour.

    Subclasses set ``_resource`` (the URL segment, e.g. ``"bridges"``) and
    ``_model`` (the pydantic model to parse into). Responses may be a bare JSON
    array or wrapped in ``{"data": ...}``; both are handled.
    """

    _resource: str
    _model: type[_ModelT]

    def __init__(self, client: UniFiProtectClient) -> None:
        """
        Initialize the endpoint.

        Args:
            client: The UniFi Protect client.

        """
        self._client = client
        # False when the most recent get_all() silently dropped an item on a
        # ValidationError. Callers need to tell a complete listing from a short
        # one: a device absent because its payload would not parse is still
        # adopted, and must not be treated as removed.
        self.last_result_complete: bool = True

    async def get_all(
        self,
        site_id: str | None = None,
        *,
        expected_unsupported: bool = False,
    ) -> list[_ModelT]:
        """
        List all resources of this device family.

        Args:
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).
            expected_unsupported: Whether a non-JSON 2xx response is an
                expected unsupported-endpoint signal - a Protect version
                without this endpoint serving its web page. Only lowers the
                log level of an unredirected response; the call still raises.

        Returns:
            List of parsed models.

        """
        path = self._client.build_api_path(f"/{self._resource}", site_id)
        self.last_result_complete = True
        response = await self._client._get(path, expected_unsupported=expected_unsupported)

        if response is None:
            return []

        data = response.get("data", response) if isinstance(response, dict) else response
        if not isinstance(data, list):
            return []

        items: list[_ModelT] = []
        for item in data:
            try:
                items.append(self._model.model_validate(item))
            except ValidationError as err:
                self.last_result_complete = False
                _LOGGER.warning(
                    "Skipping %s that failed to parse (id=%s): %s",
                    self._resource,
                    item.get("id") if isinstance(item, dict) else "?",
                    err,
                )
        return items

    async def get(self, resource_id: str, site_id: str | None = None) -> _ModelT:
        """
        Get a specific resource by ID.

        Args:
            resource_id: The resource ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).

        Returns:
            The parsed model.

        Raises:
            UniFiNotFoundError: If the response holds no resource with an ``id``.
            UniFiResponseError: If the resource in the response fails validation.

        """
        path = self._client.build_api_path(f"/{self._resource}/{resource_id}", site_id)
        record = _resource_record(await self._client._get(path))
        if record is None:
            raise UniFiNotFoundError(f"{self._resource} {resource_id} not found", status_code=200)
        try:
            return self._model.model_validate(record)
        except ValidationError as err:
            fields = sanitized_validation_fields(err)
        # Raised outside the except block: the ValidationError quotes the
        # rejected input, so it is neither chained nor kept as context.
        msg = f"{self._resource} {resource_id} response failed validation ({fields})"
        raise UniFiResponseError(msg, status_code=200)

    async def update(
        self,
        resource_id: str,
        site_id: str | None = None,
        **kwargs: Any,
    ) -> _ModelT:
        """
        Update a resource via ``PATCH``.

        A console may acknowledge a successful ``PATCH`` with an empty or
        partial body. The write has still been applied, so instead of
        failing, the resource is re-fetched with :meth:`get` and returned.

        Args:
            resource_id: The resource ID.
            site_id: The site ID (required for REMOTE connections, ignored for LOCAL).
            **kwargs: Settings to update.

        Returns:
            The updated model, from the ``PATCH`` response when it holds the
            full resource, otherwise from a follow-up ``get()``.

        Raises:
            TypeError: If ``site_id`` is neither a string nor ``None``.
            UniFiNotFoundError: If the follow-up ``get()`` finds no resource.
            UniFiResponseError: If the follow-up ``get()`` response fails validation.

        """
        if site_id is not None and not isinstance(site_id, str):
            msg = (
                f"site_id must be a str or None, not {type(site_id).__name__}; "
                "pass settings as keyword arguments"
            )
            raise TypeError(msg)
        path = self._client.build_api_path(f"/{self._resource}/{resource_id}", site_id)
        record = _resource_record(await self._client._patch(path, json_data=kwargs))
        if record is not None:
            try:
                return self._model.model_validate(record)
            except ValidationError:
                pass
        return await self.get(resource_id, site_id)


def _resource_record(response: Any) -> dict[str, Any] | None:
    """Return the single resource in a response, or None when it holds none with an ``id``."""
    if not isinstance(response, dict):
        return None
    data = response.get("data", response)
    if isinstance(data, list) and data:
        data = data[0]
    if isinstance(data, dict) and data.get("id"):
        return data
    return None
