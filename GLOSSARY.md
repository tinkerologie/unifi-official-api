# UniFi Official API

UniFi Official API lets Python applications use UniFi applications and cloud
services. This glossary gives definitions for the terms in the library.

## Language

### Applications and access

#### UniFi application

A UniFi product with its own functions and access requirements. Network,
Protect, Access, and InnerSpace are examples.

Give the name of the application when it is known.

#### Console

A UniFi system that runs applications. A Dream Machine, a Cloud Key, and a
Protect NVR are examples. A console can also route network traffic.

Use gateway for the device that sends traffic between networks.

#### API client

Software that an application uses to send requests to a UniFi application or
cloud service.

Use Network client for a device that uses the network.

#### Local connection

A direct connection to a console. It uses credentials that the console
accepts.

Use remote connection for access through the UniFi cloud connector.

#### Remote connection

A connection to a console application through the UniFi cloud connector.

Use Site Manager for the cloud service that gives console and site data.

#### Local API key

A credential for the application APIs on one console.

Use a cloud API key for cloud services and permitted remote connections.

#### Cloud API key

A credential for UniFi cloud services and permitted remote connections.

A cloud API key can have access to a subset of services or consoles.

#### Access token

The bearer credential for the UniFi Access developer interface.

Use API key for the credential of the Network or Protect API.

### Network

#### Network site

An administrative group in the Network application on one console. The site ID
has meaning only on that console.

Use Site Manager site for the cloud site record.

#### Classic site name

The site name that the Classic API uses.

Use Network site ID for the identifier from the Network Integration API.

#### Network device

Equipment that the Network application manages. Access points, switches,
gateways, and power distribution units are examples.

Use Network client for a device that uses the network.

#### Network client

A device that uses the network. A phone or a computer is an example.

Use API client for the software that sends requests to a UniFi application.

#### Gateway

A Network device that sends traffic between networks. One of those networks is
usually the internet.

Use console for a system that runs UniFi applications.

#### Network

A network segment with its own addresses, VLAN, and settings.

Use Network site for a group in the Network application.

#### Wi-Fi network

A wireless network that Network clients can connect to.

Use SSID for the name of the network.

#### SSID

A service set identifier. It gives the name of a Wi-Fi network.

Use Wi-Fi network for the full network configuration.

#### Uplink

A connection from a device to the network upstream of it.

Use WAN for the gateway's connection to the upstream network.

#### Voucher

Permission to use a hotspot. A voucher has a secret activation code and can
limit usage, time, or the number of guests.

Use service plan for a service that an administrator can give to a Carrier
Fabric subscriber.

#### Firewall policy

A Network rule that controls traffic between firewall zones.

Use ACL for an access control list.

#### ACL

An access control list. It permits traffic that meets its matching criteria.

Use firewall policy for a rule that controls traffic between zones.

#### Switch stack

A group of switch units that Network manages as one unit.

Use LAG for a group of network ports.

#### LAG

A link aggregation group. It uses more than one network port as one logical
connection.

Use switch stack for a group of switch units.

#### Network Integration API

The Network interface with versions for integration resources and operations.

Use Classic API for the earlier Network interface.

#### Classic API

An older Network API for operations that the Network Integration API does
not supply.

Use Network Integration API for the interface with versions.

### Protect

#### Protect device

Equipment that Protect manages. A camera, light, sensor, or viewer is an
example.

Use Network device for equipment that the Network application manages.

#### NVR

A network video recorder. It records video and manages Protect devices. An NVR
can be separate equipment or part of a console.

Use camera for the equipment that captures video.

#### Smart detection

A type of activity that a Protect camera identifies. A person, an animal, or a
vehicle can cause a smart detection.

Use motion detection when the camera reports movement without a specific type.

#### Liveview

A Protect layout that shows cameras in specified positions.

Use video stream for the video from one camera.

#### Talkback session

The connection information and audio format that a Protect camera gives to
send sound to its speaker.

Use video stream for the video from a Protect camera.

### Access

#### Access door

A door or gate that UniFi Access controls. It has an access control ID. UniFi
Access can report its position.

Use hub or reader for the equipment that controls entry.

#### Access device

Equipment that UniFi Access uses to control entry. A hub, reader, or intercom
is an example.

Use Access door for the entry point that UniFi Access controls.

#### Access user

A person with an identity and access rules in UniFi Access.

Use Network client for a device that uses the network.

#### Lock relay state

The locked or unlocked state of the control that operates the lock for an
Access door.

An unlocked door can stay closed.

#### Door position

The physical position that UniFi Access reports for a door or gate. The
position can be open or closed.

Use lock relay state for the locked or unlocked state.

### InnerSpace

#### InnerSpace project

An InnerSpace group that contains floor plans and the positions of UniFi
products.

Use Network site for a group in the Network application.

#### Floor plan

A drawing of a physical space in InnerSpace. InnerSpace can show the positions
of UniFi products on this drawing.

Use Network site for the group in the Network application.

#### Placed product

A UniFi product with a position on a floor plan in an InnerSpace project.

Use the InnerSpace product ID for this product. Network and Protect have their
own device IDs.

### Cloud services

#### Site Manager host

A console that UniFi Site Manager identifies and reports data for.

Use hostname for the name used to find a system on the network.

#### Site Manager site

A cloud site record for a Site Manager host.

Use Network site for the site record from the Network application.

#### Mobility workspace

An administrative group for mobile routers and their administrators in UniFi
Mobility.

Use Carrier Fabric organization for the administrative group in Carrier
Fabric.

#### Mobile router

A router that UniFi Mobility manages. Mobility reports the router's
connections and cellular service.

Use gateway for a Network device that sends traffic between networks.

#### Carrier Fabric organization

An administrative group for subscribers and service plans in Carrier Fabric.

A fabric is a separate resource in Carrier Fabric.

#### Subscriber

A customer or service subscription with a subscriber ID in Carrier Fabric. A
subscriber can have a service plan and a host.

Use Network client for a device that uses the network.

#### Service plan

A Carrier Fabric service that an administrator can give to a subscriber.

Use subscriber for the customer or service subscription.

#### Host assignment

The relation between a Carrier Fabric subscriber and its gateway host.

Use service plan for the service that an administrator can give to a
subscriber.
