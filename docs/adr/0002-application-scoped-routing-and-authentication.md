# Application-scoped routing and authentication

**Status:** Accepted; recorded retrospectively on 2026-11-07.

Each UniFi application or cloud service has its own client and resource
operations. Network, Protect, and InnerSpace clients construct their local or
cloud-connector paths centrally; Network also exposes explicit classic API
paths. Site Manager, Mobility, and Carrier Fabric retain their own cloud
interfaces. Access uses its separate console developer interface and bearer
token rather than borrowing Network or Protect credentials.

The shared transport hides HTTP mechanics while application clients retain
knowledge of route families, identifiers, and authentication. A universal
resource client would make callers supply those details themselves; separate
HTTP implementations would duplicate connection and error policy.

## Consequences

- A console identity, Network site identity, classic site name, and cloud
  service scope are distinct inputs; callers cannot substitute one for another.
- The presence of a client method does not imply that every application
  supports every connection mode.
- Classic Network operations remain explicit compatibility surfaces rather
  than being presented as documented Integration API operations.
- Resource groups share transport behavior without requiring identical
  resource layouts in every application.

## Evidence

- [Network client and path builders](../../src/unifi_official_api/network/client.py),
  [Protect client](../../src/unifi_official_api/protect/client.py), and
  [Access client](../../src/unifi_official_api/access/client.py).
- [Network conformance tests](../../tests/network/test_spec_conformance.py),
  [Protect conformance tests](../../tests/protect/test_spec_conformance.py), and
  [Access client tests](../../tests/test_api_access_client.py).
