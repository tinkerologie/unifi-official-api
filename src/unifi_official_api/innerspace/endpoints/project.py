"""Project endpoint for UniFi InnerSpace API."""

from typing import TYPE_CHECKING, Any

from ...exceptions import UniFiResponseError
from ..models import InnerSpaceProject

if TYPE_CHECKING:
    from ..client import UniFiInnerSpaceClient

_KNOWN_PROJECT_KEYS = frozenset(
    {
        "project",
        "plans",
        "products",
        "wall_types",
        "wallTypes",
        "attenuation_object_types",
        "attenuationObjectTypes",
        "shapes",
        "id",
        "title",
        "name",
        "model",
        "environment",
    }
)


class ProjectEndpoint:
    """Endpoint for ``GET /v1/project``."""

    def __init__(self, client: UniFiInnerSpaceClient) -> None:
        self._client = client

    async def get(
        self,
        mode: str | None = None,
        *,
        expected_unsupported: bool = False,
    ) -> InnerSpaceProject:
        """Fetch the InnerSpace project, plans, and placed products."""
        params: dict[str, Any] | None = {"mode": mode} if mode else None
        path = self._client.build_api_path("/project")
        response = await self._client._get(
            path,
            params=params,
            expected_unsupported=expected_unsupported,
        )
        if not isinstance(response, dict):
            msg = "/v1/project returned a malformed response"
            raise UniFiResponseError(msg, status_code=200)

        payload = response.get("data") if "data" in response else response
        if payload is None:
            return InnerSpaceProject()
        if not isinstance(payload, dict):
            msg = "/v1/project returned a malformed response"
            raise UniFiResponseError(msg, status_code=200)

        if payload and not (payload.keys() & _KNOWN_PROJECT_KEYS):
            msg = "/v1/project returned a malformed response"
            raise UniFiResponseError(msg, status_code=200)

        return InnerSpaceProject.model_validate(payload)


__all__ = ["ProjectEndpoint"]
