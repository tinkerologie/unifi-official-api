# Forward-compatible typed resource models

**Status:** Accepted; recorded retrospectively on 2026-11-07.

Resource responses use Pydantic models with Python field names and aliases for
upstream names. Many models retain unknown fields so firmware additions do not
require an immediate library release. Selected evolving enum fields accept
known enum values first and retain unknown strings; this is a field-specific
choice rather than a promise that every model field accepts arbitrary values.

Typed records give consumers a stable vocabulary without discarding new
upstream information. Raw dictionaries would move parsing into every consumer;
rejecting all extra fields would couple consumers to every firmware addition.
Required fields and application-specific validators still determine whether a
record is usable.

## Consequences

- Adding an unknown field is different from changing the type or omitting a
  required field; forward compatibility does not make malformed records valid.
- Python field names and upstream aliases serve different serialization needs.
  Callers choose alias serialization when constructing upstream-shaped data.
- Known enum values may be canonicalized, while an unfamiliar value remains a
  string only on fields that explicitly support that behavior.

## Evidence

- [Network client model](../../src/unifi_official_api/network/models/client.py)
  and [site model](../../src/unifi_official_api/network/models/site.py).
- [Carrier Fabric models](../../src/unifi_official_api/carrier_fabric/models.py).
- [Enum-union tests](../../tests/test_enum_unions.py) and
  [Network model tests](../../tests/network/test_models.py).
- [Changelog](../../CHANGELOG.md), especially the 3.0.1 enum compatibility change.
