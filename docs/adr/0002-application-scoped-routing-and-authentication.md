# Application-scoped routing and authentication

**Status:** Accepted. The record date is 2026-11-07.

Each UniFi application or cloud service has its own client. The client gives
access to its resources. Network, Protect, and InnerSpace clients have
functions that make local and cloud connector paths. Network also has
functions that make Classic API paths.

Site Manager, Mobility, and Carrier Fabric have separate cloud interfaces.
Access uses its console developer interface. This interface uses an Access
token.

The shared transport manages HTTP requests. The application client selects
the path, identifiers, and credentials. Without an application client, the
caller must supply these details. Separate HTTP code for each application
repeats the connection and error rules.

## Consequences

- A console ID, a Network site ID, a classic site name, and a cloud service
  scope are different inputs.
- The application determines the connection modes that a client method can use.
- Classic API operations use a separate interface from Network Integration API
  operations.
- The same transport can send requests for different resource layouts.

## Evidence

- [Network client and path builders](../../src/unifi_official_api/network/client.py),
  [Protect client](../../src/unifi_official_api/protect/client.py), and
  [Access client](../../src/unifi_official_api/access/client.py).
- [Network conformance tests](../../tests/network/test_spec_conformance.py),
  [Protect conformance tests](../../tests/protect/test_spec_conformance.py), and
  [Access client tests](../../tests/test_api_access_client.py).
