# Forward-compatible typed resource models

**Status:** Accepted. The record date is 2026-11-07.

The library uses Pydantic models for resource responses. A model can use a
Python field name and an alias for the API field name. Many models keep
fields that the library does not know. This lets an application read a field
that a firmware update adds before the next library release.

Some enum fields accept both known values and unknown strings. Each model
specifies which fields can do this. Required fields and validators determine
if a record is valid.

If the library returned raw dictionaries, each caller would need to parse
them. If the library refused all unknown fields, each new field would
require a library release.

## Consequences

- An unknown field can be valid. A field with the wrong type or a missing
  required field can make a record invalid.
- To make data with API field names, use alias serialization.
- A model can convert a known value to its enum value. It keeps an unknown
  value as a string only for fields that permit it.

## Evidence

- [Network client model](../../src/unifi_official_api/network/models/client.py)
  and [site model](../../src/unifi_official_api/network/models/site.py).
- [Carrier Fabric models](../../src/unifi_official_api/carrier_fabric/models.py).
- [Enum-union tests](../../tests/test_enum_unions.py) and
  [Network model tests](../../tests/network/test_models.py).
- [Changelog](../../CHANGELOG.md), especially the 3.0.1 enum compatibility change.
