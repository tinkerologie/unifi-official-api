"""NAT rule data model for UniFi Network API."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def is_predefined_nat_rule(rule_data: Any) -> bool:
    """
    Return True when a NAT rule is managed by the controller, not the user.

    Reference-derived (sirkirby/unifi-mcp ``_editable``): a rule is predefined
    when ``is_predefined`` is True, or when ``setting_preference`` is present
    and is not ``"manual"``. A record that carries neither key is a user rule.
    """
    if not isinstance(rule_data, dict):
        return False
    if rule_data.get("is_predefined") is True:
        return True
    return "setting_preference" in rule_data and rule_data["setting_preference"] != "manual"


class NatRule(BaseModel):
    """
    Custom NAT rule in UniFi Network (v2 ``/nat``).

    Reference shape, not observed on a live console (0 records on Network 11,
    2026-10-12). Keys per the sirkirby/unifi-mcp Network 10.6 fixture:
    _id, description, destination_filter, enabled, exclude, in_interface,
    ip_address, ip_version, is_predefined, logging, port, pppoe_use_base_interface,
    protocol, rule_index, setting_preference, source_filter, type.

    Only id, description and enabled are declared; every other key is kept as an
    extra so a type change on the controller cannot make a record fail validation
    (a skipped record would look deleted to the switch orphan prune).
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str = Field(alias="_id")
    description: str | None = None
    enabled: bool | None = None

    @field_validator("enabled", mode="before")
    @classmethod
    def _enabled_must_be_bool(cls, value: Any) -> bool | None:
        """
        Ensure enabled is strictly boolean or None without type coercion.
        """
        return value if isinstance(value, bool) else None
