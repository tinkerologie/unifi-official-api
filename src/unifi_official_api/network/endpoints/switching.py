"""Switching endpoint for UniFi Network API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...validation import parse_record, require_record
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
            return parse_record(LagPage, response, "LAG page")
        return LagPage(data=[])

    async def get_lag(self, site_id: str, lag_id: str) -> Lag:
        path = self._client.build_api_path(f"/sites/{site_id}/switching/lags/{lag_id}")
        return require_record(await self._client._get(path), Lag, f"LAG {lag_id}")

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
            return parse_record(McLagDomainPage, response, "MC-LAG domain page")
        return McLagDomainPage(data=[])

    async def get_mc_lag_domain(self, site_id: str, domain_id: str) -> McLagDomain:
        path = self._client.build_api_path(f"/sites/{site_id}/switching/mc-lag-domains/{domain_id}")
        return require_record(
            await self._client._get(path),
            McLagDomain,
            f"MC-LAG domain {domain_id}",
        )

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
            return parse_record(SwitchStackPage, response, "Switch stack page")
        return SwitchStackPage(data=[])

    async def get_switch_stack(self, site_id: str, stack_id: str) -> SwitchStack:
        path = self._client.build_api_path(f"/sites/{site_id}/switching/switch-stacks/{stack_id}")
        return require_record(
            await self._client._get(path),
            SwitchStack,
            f"Switch stack {stack_id}",
        )
