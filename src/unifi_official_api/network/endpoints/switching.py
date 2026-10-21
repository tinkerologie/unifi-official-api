"""Switching endpoint for UniFi Network API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..models.switching import (
    Lag,
    LagPage,
    McLagDomain,
    McLagDomainPage,
    SwitchStack,
    SwitchStackPage,
)

if TYPE_CHECKING:
    from ..client import UniFiNetworkClient


class SwitchingEndpoint:
    """Endpoint for managing switching features (LAGs, MC-LAG, Switch Stacks)."""

    def __init__(self, client: UniFiNetworkClient) -> None:
        self._client = client

    async def get_lags(
        self,
        site_id: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> LagPage:
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        path = self._client.build_api_path(f"/sites/{site_id}/switching/lags")
        response = await self._client._get(path, params=params if params else None)
        if isinstance(response, dict):
            return LagPage.model_validate(response)
        return LagPage(data=[])

    async def get_lag(self, site_id: str, lag_id: str) -> Lag:
        path = self._client.build_api_path(f"/sites/{site_id}/switching/lags/{lag_id}")
        response = await self._client._get(path)
        if isinstance(response, dict):
            data = response.get("data", response)
            if isinstance(data, dict) and "id" in data:
                return Lag.model_validate(data)
        raise ValueError(f"LAG {lag_id} not found")

    async def get_mc_lag_domains(
        self,
        site_id: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> McLagDomainPage:
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        path = self._client.build_api_path(f"/sites/{site_id}/switching/mc-lag-domains")
        response = await self._client._get(path, params=params if params else None)
        if isinstance(response, dict):
            return McLagDomainPage.model_validate(response)
        return McLagDomainPage(data=[])

    async def get_mc_lag_domain(self, site_id: str, domain_id: str) -> McLagDomain:
        path = self._client.build_api_path(f"/sites/{site_id}/switching/mc-lag-domains/{domain_id}")
        response = await self._client._get(path)
        if isinstance(response, dict):
            data = response.get("data", response)
            if isinstance(data, dict) and "id" in data:
                return McLagDomain.model_validate(data)
        raise ValueError(f"MC-LAG domain {domain_id} not found")

    async def get_switch_stacks(
        self,
        site_id: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> SwitchStackPage:
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        path = self._client.build_api_path(f"/sites/{site_id}/switching/switch-stacks")
        response = await self._client._get(path, params=params if params else None)
        if isinstance(response, dict):
            return SwitchStackPage.model_validate(response)
        return SwitchStackPage(data=[])

    async def get_switch_stack(self, site_id: str, stack_id: str) -> SwitchStack:
        path = self._client.build_api_path(f"/sites/{site_id}/switching/switch-stacks/{stack_id}")
        response = await self._client._get(path)
        if isinstance(response, dict):
            data = response.get("data", response)
            if isinstance(data, dict) and "id" in data:
                return SwitchStack.model_validate(data)
        raise ValueError(f"Switch stack {stack_id} not found")
