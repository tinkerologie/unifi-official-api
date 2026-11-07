# Operation-specific response validation

**Status:** Accepted. The record date is 2026-11-07.

Response helpers tell the caller if a record is missing or invalid. They also
report a create response without a usable ID and an update response that
needs a read. A validation error for one record gives the names of the
fields with errors. It omits the rejected input. These rules started in
version 3.0.0.

An HTTP success code can occur with an invalid record. An empty write
response can occur after a successful write. When an update response has no
record, the caller can use the known ID to read it. When a create response
has no usable ID, the caller cannot use this procedure. The resource can
already exist.

## Consequences

- `require_record` gives different errors for missing and invalid records,
  including responses with HTTP 200.
- `created_record` reports that the resource can already exist when the
  response gives no usable record.
- `written_record` returns `None` if the response contains no usable record.
  The caller can then read the resource by its known ID.
- A strict listing raises an exception for an invalid record. Some listings
  skip invalid records. The legacy completeness flag can change between reads.

## Protect listing update

For Protect inventory, `get_all_result()` gives the records and completeness
flag from one request. A valid empty list, an invalid record, and an invalid
list shape give different results. For rejected records, both listing
methods log only information from the schema.

## Evidence

- [Shared validation helpers](../../src/unifi_official_api/validation.py).
- [Protect device endpoints](../../src/unifi_official_api/protect/endpoints/_base.py).
- [Malformed-response tests](../../tests/test_malformed_responses.py).
- [3.0.0 response-contract changes](../../CHANGELOG.md).
