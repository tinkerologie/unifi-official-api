# UniFi Official API

This library exposes UniFi applications and cloud services to Python consumers.
The glossary distinguishes their resources and identities without prescribing
how an application represents them.

## Language

### Applications and access

**UniFi application**:
A UniFi product with its own resources and capabilities, such as Network,
Protect, Access, or InnerSpace.
_Avoid_: domain without a qualifier.

**Console**:
A UniFi system hosting applications, such as a Dream Machine, Cloud Key, or
Protect NVR. A console can also perform a gateway role.
_Avoid_: controller or gateway as a synonym for every console.

**API client**:
The library's connection to a UniFi application or cloud service on behalf of
a consuming application.
_Avoid_: client without a qualifier.

**Local connection**:
Access made directly to a console using credentials accepted by that console.
_Avoid_: cloud connector connection.

**Remote connection**:
Access to a console application through UniFi's cloud connector.
_Avoid_: Site Manager as a synonym for every remote operation.

**Local API key**:
A credential issued for access to a console's supported application APIs.
_Avoid_: cloud API key or Access token as an interchangeable credential.

**Cloud API key**:
A credential for UniFi cloud services and permitted remote console access.
_Avoid_: assuming one key grants every service or console permission.

**Access token**:
The bearer credential for the UniFi Access developer interface.
_Avoid_: Network API key or Protect API key.

### Network

**Network site**:
An administrative grouping within a console's Network application, with an
identity meaningful in that console's scope.
_Avoid_: physical location, VLAN, console, or Site Manager site as a synonym.

**Classic site name**:
The site reference used by the older Network controller interface.
_Avoid_: assuming it is interchangeable with the Network Integration site ID.

**Network device**:
Managed Network infrastructure, such as an access point, switch, gateway, or
power distribution unit.
_Avoid_: Network client.

**Network client**:
An endpoint using the network, such as a phone, computer, or connected guest.
_Avoid_: client without a qualifier, API client, or Network device.

**Gateway**:
A Network device routing traffic between networks, commonly including an
internet connection.
_Avoid_: console when only the routing role is meant.

**Network**:
A configured network segment with its addressing, VLAN, and related settings.
_Avoid_: Network site or Wi-Fi network as an interchangeable concept.

**Wi-Fi network**:
A configured wireless network through which Network clients can connect.
_Avoid_: SSID when the complete configuration is meant.

**SSID**:
The name identifying a Wi-Fi network to wireless clients.
_Avoid_: site name or the entire Wi-Fi configuration.

**Uplink**:
The connection from a device or client toward its upstream network attachment.
_Avoid_: WAN when referring to another local device.

**Voucher**:
A hotspot access entitlement with a secret activation code and optional usage,
duration, or guest limits.
_Avoid_: subscriber service plan or general API credential.

**Firewall policy**:
A Network rule controlling traffic between the zones to which it applies.
_Avoid_: traffic rule, route, or ACL as an interchangeable rule family.

**ACL**:
An access control list governing permitted traffic according to its supported
matching criteria.
_Avoid_: firewall policy as a universal synonym.

**Switch stack**:
A group of switch units represented and managed as one stack.
_Avoid_: a single switch or a link aggregation group.

**LAG**:
A link aggregation group combining multiple network ports into one logical
connection.
_Avoid_: switch stack.

**Network Integration API**:
The versioned Network interface for the application's supported integration
resources and operations.
_Avoid_: classic API when describing Integration API resources.

**Classic API**:
The older Network controller interfaces retained for supported operations not
provided by the Network Integration API.
_Avoid_: treating classic and Integration API site identities as interchangeable.

### Protect

**Protect device**:
Equipment managed by Protect, such as a camera, light, sensor, or viewer.
_Avoid_: Network device as an interchangeable resource identity.

**NVR**:
The system hosting Protect's video recording and device management, whether
dedicated hardware or part of a console with other roles.
_Avoid_: camera or assuming it must be a separate appliance.

**Smart detection**:
A Protect camera's classification of activity, such as a person, animal, or
vehicle detection.
_Avoid_: motion detection when a specific classification is meant.

**Liveview**:
A named Protect layout assigning cameras to viewing slots.
_Avoid_: a camera's individual video stream.

**Talkback session**:
A camera-negotiated destination and audio format for transmitting sound to a
Protect camera's speaker.
_Avoid_: camera video stream or liveview.

### Access

**Access door**:
A managed entry point with its own access-control identity and optional
physical-position information.
_Avoid_: hub or reader as a synonym for the entry point.

**Access device**:
Access equipment such as a hub, reader, or intercom associated with entry
control.
_Avoid_: Access door or Network device as an interchangeable resource.

**Access user**:
A person represented by UniFi Access with access-related identity and policy
information.
_Avoid_: Network client or cloud account as an interchangeable identity.

**Lock relay state**:
The locked or unlocked state of an Access door's lock control.
_Avoid_: door position; an unlocked door can remain physically closed.

**Door position**:
The physical open or closed state reported for an Access entry point.
_Avoid_: lock relay state.

### InnerSpace

**InnerSpace project**:
A spatial project containing floor plans and UniFi product placements.
_Avoid_: Network site or Mobility workspace.

**Floor plan**:
An InnerSpace representation of a physical space on which UniFi products can
be located.
_Avoid_: network topology or Network site.

**Placed product**:
A UniFi product associated with a floor plan in an InnerSpace project.
_Avoid_: assuming its InnerSpace identity is a Network or Protect device ID.

### Cloud services

**Site Manager host**:
A console represented in UniFi Site Manager, with cloud identity and reported
state information.
_Avoid_: hostname, physical location, or Network client.

**Site Manager site**:
A cloud site record associated with a Site Manager host.
_Avoid_: assuming its identity can replace a Network site identity.

**Mobility workspace**:
A UniFi Mobility administrative grouping for mobile routers and their
administrators.
_Avoid_: Network site or Carrier Fabric organization.

**Mobile router**:
A router managed by UniFi Mobility, with connectivity and cellular-service
information.
_Avoid_: Network client or treating every Network gateway as a Mobility router.

**Carrier Fabric organization**:
The administrative scope for Carrier Fabric subscribers and service plans.
_Avoid_: Network site or fabric as an interchangeable name.

**Subscriber**:
A Carrier Fabric customer or service subscription with its own subscriber
identity and optional service-plan and host associations.
_Avoid_: device, Network client, or Network site.

**Service plan**:
A Carrier Fabric service offering that can be assigned to subscribers.
_Avoid_: subscriber or InnerSpace floor plan.

**Host assignment**:
The association between a Carrier Fabric subscriber and its gateway host.
_Avoid_: service-plan assignment; these are separate relationships.
