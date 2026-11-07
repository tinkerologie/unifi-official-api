# Operation-specific response validation

**Status:** Accepted; recorded retrospectively on 2026-11-07.

Shared response helpers distinguish a missing record, a malformed record, a
create response without a usable new identity, and an acknowledged write that
needs a follow-up read. Single-record parsing raises library exceptions with
sanitized field names instead of exposing Pydantic's rejected inputs through
the exception chain. These public response contracts were established in 3.0.0.

An HTTP success does not establish that a returned resource is valid, and an
empty write response does not establish that the write failed. A getter can
report absence, an update can re-fetch a known identity, and a create without
its new identity must report uncertainty rather than encouraging a blind retry.
Treating all three as the same parsing failure would lose that information.

## Consequences

- `require_record` differentiates an absent record from one that fails
  validation, even when the server returned HTTP 200.
- `created_record` reports that the resource may already have been created when
  its response supplies no usable record.
- `written_record` lets an update re-fetch rather than declaring a successful
  write failed merely because its acknowledgement is empty or partial.
- List handling has two existing policies: strict listings fail on malformed
  records; some lenient listings skip them and expose completeness separately.
  That mutable completeness flag must be paired with the relevant read.
- Sanitized helper exceptions do not guarantee that every endpoint's logging
  follows the same policy; lenient list parsing remains endpoint-specific.

## Evidence

- [Shared validation helpers](../../src/unifi_official_api/validation.py).
- [Protect device endpoints](../../src/unifi_official_api/protect/endpoints/_base.py).
- [Malformed-response tests](../../tests/test_malformed_responses.py).
- [3.0.0 response-contract changes](../../CHANGELOG.md).
