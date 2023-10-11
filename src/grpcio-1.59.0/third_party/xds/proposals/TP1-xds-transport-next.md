TP1: xdstp:// structured resource naming, caching and federation support.
----
* Author(s): Harvey Tuch, Louis Ryan, Mark Roth, Costin Manolache, Matt Klein
* Approver:
* Implemented in: <xDS client, ...>
* Last updated: 2021-08-21

## Abstract

This proposal describes a set of related changes to the [xDS transport
protocol](https://www.envoyproxy.io/docs/envoy/latest/api-docs/xds_protocol)
aimed at supporting caching, federation, scalability and improved reliability of
the xDS transport.

These changes are motivated by the growth of the xDS ecosystem, including client
diversity, range of deployments, layering of config/control pipelines and desire
for hybrid control plane topologies in the xDS community.

We introduce a new structured resource naming format based on Uniform Resource
Identifiers (URIs) with the `xdstp://` scheme.  xDS resource names can now
function as independent cache keys without requiring additional transport
context. In addition, resource names support a notion of named authority,
namespace delegation and failover.

A distinction between resource singletons and collections is also included in
the transport protocol. This formalizes some of the loose conventions that
Envoy's use of xDS had established and allows for generalization for use cases
such as [LEDS](https://github.com/envoyproxy/envoy/issues/10373).  These changes
help to eliminate technical debt in the transport protocol, by removing special
case treatment of LDS and CDS in xDS, deprecating resource name aliases and
aligning the future of the transport protocol behind delta xDS.

## Background

Since the introduction of v2 xDS in Envoy, the transport protocol has provided a
generic pub-sub mechanism between client (Envoy) and management server (xDS
control plane). The resources have been opaque, identified by a type
URL, opaque resource name string and opaque version string.

For example, a route configuration resource named `foo` would have type URL
`envoy.config.route.v3.RouteConfiguration` and a version string such as `42-a`.

In addition, control planes have interpreted the
[`Node`](https://www.envoyproxy.io/docs/envoy/latest/api-v3/config/core/v3/base.proto#envoy-v3-api-msg-config-core-v3-node)
message presented at the start of an xDS transport stream to provide further
contextual information, for example node ID, locality, credentials, tenancy information, 
user agent, local environment configuration, etc. In general,
arbitrary key-value metadata is expressible in the `Node` message.

While the xDS resource naming scheme above identifies a single resource, special case
provisions were needed for collections; LDS and CDS resource collections were treated in a
distinguished manner by interpreting empty resources request sets as wildcards.

An Aggregated Discovery Stream (ADS) was introduced to Envoy to support
greater efficiency, server stickiness and better-than-eventual consistency for
API updates. A single control plane server was assumed, since Envoy had
mostly been used in direct client-server applications.

While this has been sufficient for many use cases to date, a number of limitations
have become evident which this proposal addresses. These are enumerated in the
following sub-sections.

### Caching & Scalability

As the xDS and Envoy ecosystems have grown, so has the number of applications where xDS
finds itself used. Some of these applications require caching of xDS resources,
for example:

*   Scalable control planes that deal with the problem of client fan-out. An
    example of a project tackling this is
    [xds-relay](https://github.com/envoyproxy/xds-relay).
*   Hybrid on-premise/cloud clients and control planes. Resources might be
    cached
    on-premise to enhance reliability in the event of an interconnect outage.
*   Mobile and edge, where an xDS client such as Envoy runs in mobile
    applications with `O(millions+)` of xDS clients interacting with a control
    plane. An example project in this space is [Envoy
    Mobile](https://github.com/envoyproxy/envoy-mobile).

In some cases, control planes have been observed as treating xDS resources as *mutable*. Depending on the
contents of the `Node` message (which may change over the lifetime of an xDS
transport stream), they can provide the same resource `foo` at a given version
with different values.

This impacts cacheability; the `Node` message becomes part of the cache key (and
must be distributed across [xDS
relays](https://docs.google.com/document/d/1X9fFzqBZzrSmx2d0NkmjDW2tc8ysbLQS9LaRQRxdJZU/edit?disco=AAAAGQ_84vU&ts=5e61532c&usp_dm=false)).
This conflates client identity with resource identity. Some of the `Node`
message is only relevant on a single hop to the management server, but in more
complex topologies other attributes (e.g. metadata) are what really matter when
trying to fetch a resource.

The proposal below introduces *immutable* resource names which fully encapsulate
resource context; an xDS resource name URI is a cache key, control planes are
expected to provide resource [idempotence](https://restfulapi.net/idempotent-rest-apis/) for
client resource fetches at a given resource version.

### Federation

xDS federation describes an xDS client that fetches resources from more than one
management server. A single xDS client's configuration is disaggregated across
multiple authorities. Other features of federation include delegation of
authority between management servers, failover and support for hybrid topologies
(e.g. on-premise/cloud, cloud A/B). Some example use cases:

*   Failover from a Control Plane as-a-service (CPaaS) to an on-premise control
    plane during a network partition.
*   On-premise authoring and publication of xDS fragments to a CPaaS.
*   Disaggregating responsibility for load balancing APIs between on-premise and
    CPaaS. For example splitting the health check and load assignment
    responsibilities.
*   Disaggregating an xDS control plane internally. Complex xDS control planes
    may benefit from having multiple independent xDS providers with limited
    coupling.
*   Bridging independent service meshes with independent control planes.

While there are many challenges in xDS federation, including:

* Trust management, e.g. resource signing.
* Improving resource composition and granularity when splitting provenence.
* Coordination over authority delegation between management servers.

we do not aim to tackle all of these below, instead restricting the proposal to
a structured naming scheme that will provide the basis for future solutions to
the full set of federation concerns.

We define a control plane serving a given xDS resource as an *authority*. The
proposal below introduces indirection to avoid the existing xDS conflation between the
naming of an authority and the configuration of fetches from the authority (a
[`ConfigSource`](https://www.envoyproxy.io/docs/envoy/latest/api-v3/config/core/v3/config_source.proto#envoy-v3-api-msg-config-core-v3-configsource)
message). This conflation makes it challenging to use multiple authorities today
and contributes to configuration size scalability problems when federating.
The proposal includes the authority in the xDS resource name URI.

### xDS transport protocol technical debt

Since the xDS transport protocol has been historically co-developed with the
Envoy implementation, this close coupling and evolution (vs. upfront design) has
given rise to acknowledged technical debt relating to resource naming and typing.

#### Flat representation

Today, resource identifies are a hodge podge of resource name, `Node` message,
authority from `ConfigSource`, type URL and version. When communicating between
humans or systems that don’t work with proto3 messages, there is no standard
format for concisely encoding this information.

URIs provide a powerful standards compliant way of specifying this information.

#### Collections

Using terminology from [REST resource
naming](https://restfulapi.net/resource-naming/), xDS supports both singleton
and collection discovery. For xDS types such as RDS/EDS/SDS, singleton
resource names are provided explicitly in the discovery request, and returned.
For other xDS types, e.g. CDS/LDS, an implicit wildcard name is expressed
via an empty request resource name set.

The limitations of this approach for collections become apparent when you
consider what might be needed to select a subset of listeners or clusters via
LDS/CDS. Often `Node` metadata is used for this purpose, which conflates node
identity with per-resource type naming semantics.  Reasons to subset the
universe of resources for a given type include:

* Differentiating inbound/outbound listeners in a service mesh topology.
* Sharding tenant listeners between different nodes in a multi-tenant proxy
  fleet.
* Distinguishing based on node function in a service mesh (e.g. ingress/egress).

Collection namespacing is also necessary for scalable endpoint support
in [LEDS](https://github.com/envoyproxy/envoy/issues/10373).

In the proposal below, we introduce an explicit notion of collections and
namespaces, expressed through xDS resource name URIs.

#### Per-resource type transport naming semantics

While most xDS resource types permit opaque resource naming at the discretion of
the control plane, some xDS resources, namely VHDS, have specific resource
name structure. VHDS requires a specific form
[form](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_conn_man/vhds.html?highlight=vhds#virtual-host-resource-naming-convention)
for referenced resources, `<route configuration name>/<host entry>`. This permits the management
server to lookup a  missing virtual host with the host entry inside the
specified `RouteConfiguration` resource name. In this scheme, the route
configuration name is acting as a namespace for the virtual host name.

It’s likely other resource types in the future will require some structure, e.g.
[LEDS](https://github.com/envoyproxy/envoy/issues/10373).  Rather than living
with an arbitrary mix of opaque and structured forms, the URI-based xDS resource
naming scheme below provides a structured scheme that can serve the
expression needs of resource types such as VHDS and LEDS.

#### Aliasing

VHDS introduced aliasing to the xDS transport, since the same virtual host
resource may be known by multiple names, e.g. `routeConfigA/foo.com,
routeConfigA/bar.com`. This mechanism is not widely used yet elsewhere in xDS
and it is another example of mixing the transport and data model resource layers
in xDS.

We introduce a redirection mechanism below that allows a control plane to
provide aliasing semantics without requiring explicit transport-level support
for aliasing. When querying for either `routeConfigA/foo.com` or `routeConfigA/bar.com`, the
management server might issue a redirect causing the xDS client to fetch
`someCanonicalVirtualHost` resource.

This same mechanism is also useful when supporting resource delegation during
federation and removes special case treatment of aliasing from the xDS transport
protocol.

### Related Proposals:

* The original Google Docs design documents:
  [Full](https://docs.google.com/document/d/1zZav-IYxMO0mP2A7y5XHBa9v0eXyirw1CxrLLSUqWR8/edit#heading=h.w8hw2zbv3jwl)
  [Summary](https://docs.google.com/document/d/1m5_Q9LUlzvDdImP0jqh1lSTrLMldsApTQX6ibbd3i7c/edit?ts=5ec2fd8a#heading=h.w8hw2zbv3jwl)
* [xDS transport protocol.](https://www.envoyproxy.io/docs/envoy/latest/api-docs/xds_protocol)

## Proposal

The proposal below is fully backwards compatible with the existing xDS transport
protocol and does not require any changes to clients or servers that do not wish
to opt into the new naming scheme.

### URI-based xDS resource names

xDS URIs follow a [RFC-3986](https://tools.ietf.org/html/rfc3986) compliant
schema. The following schema is proposed for xDS resource names:

`xdstp://[{authority}]/{resource type}/{id/*}?{context parameters}{#processing directive,*}`

* `authority` is an opaque string naming a resource authority, e.g.
  `some.control.plane`.
* `resource type` is the xDS resource type URL, e.g. `envoy.config.route.v3.RouteConfiguration`
* `id/*` is the remaining path component of the URI and is fully opaque; naming
  is at the discretion of the control plane(s).
* `context parameters` are the URI query parameters and express contextual
  information for selecting resource variants, for example `shard_id=1234&direction=inbound`.
* A `processing directive` provides additional information to the client on how
  the URI is to be interpreted. Two supported directives are:
  * `alt=<xdstp:// URI>` expressing a fallback URI.
  * `entry=<resource name>` providing an anchor referring to an inlined resource
    for [list collections](#list). Resource names must be of the form `[a-zA-Z0-9_-\./]+`.

Multiple directives are comma separated in the fragment component of the URI.
The same directive may not appear more than once in a given URI.

An example application of the above URI scheme is:

`xdstp://some.control.plane/envoy.config.route.v3.RouteConfiguration/foo/bar?shard_id=1234&direction=inbound`

We distinguish between two forms of `xdstp://` URIs:

* Uniform Resource Locators (URLs) instructing a client on how to locate a given
  xDS resource. URLs may include processing directives and [globs](#glob).

* Uniform Resource Names (URNs) referring to a specific xDS resource. URNs do
  not include processing directives or [globs](#glob). `xdstp://` URNs provide
  self-contained cache keys.

#### Proto3 expression

`xdstp://` URIs are canonically encoded in `proto3` messages. The structure
for this encoding is provided at https://github.com/cncf/xds/tree/main/xds/core/v3:

* [URL](https://github.com/cncf/xds/blob/main/xds/core/v3/resource_locator.proto) definition
* [URN](https://github.com/cncf/xds/blob/main/xds/core/v3/resource_name.proto) definition

#### Normalization

Two `xdstp://` URNs are considered equivalent if they match component-wise
modulo context parameter ordering.

#### Context parameters

Context parameters in URNs presented by the client to the server will be
composed from the following sources. Using an example of a URL
`xdstp://some-authority/some.type/foo?bar=baz`:

* Context parameters from the URL, in the above example
  `bar=baz`. These must not be in the `xds.*` namespace.

* Per-resource type well-known attributes, e.g. an on-demand listener load might
  have `{xds.resource.vip: 96.54.3.1}`. These attributes are generated by code,
  e.g. an on-demand LDS implementation will first detect the VIP, halt the
  request, ask for the `xds.resource.vip` from the control plane, and then
  resume the request after discovery is completed. All these attributes will be
  `xds.resource.` prefixed.

An example computed URN following the above example is
`xdstp://some-authority/some.type/foo?bar=baz&xds.resource.vip=96.54.3.1`.

This proposal reserves all prefixes beginning with a non-alphanumeric character
for context parameter values in future URI context parameter enhancements.

### Collections

Two forms of resources collections are described below, *list* and *glob*. These
different forms reflect the tension between the need for explicit collection
representation (motivating list collections) and scalability concerns as this
explicit representation becomes a bottleneck (motivating [glob](#glob) collections).

Collections are typically used for LDS, CDS and (planned) LEDS. However, this
list is not exhaustive and future xDS collection types may be added with no
change to the transport protocol.

#### List

List collections provide a collection directory as a first-class xDS resource.
For a given xDS resource type `<T>` the list collection type is named by
convention as `<T>Collection` and defined as:

```
message <T>Collection {
  repeated CollectionEntry resources = 1;
}
```

where `CollectionEntry` is defined:


```
message CollectionEntry {
  // Inlined resource entry.
  message InlineEntry {
    // Optional name to describe the inlined resource. Resource names must
    // [a-zA-Z0-9_-\./]+. This name allows reference via the #entry directive
    // in ResourceLocator. When non-empty, this name must be unique in any give
    // list collection.
    string name = 1 [(validate.rules).string.pattern = "^[0-9a-zA-Z_\\-\\.~:]+$"];

    // The resource's logical version. It is illegal to have the same named xDS
    // resource name at a given version with different resource payloads.
    string version = 2;

    // The resource payload, including type URL.
    google.protobuf.Any resource = 3;
  }

  oneof resource_specifier {
    option (validate.required) = true;

    // A xdstp:// URL describing how the member resource is to be located.
    string locator = 1;

    // The resource is inlined in the list collection.
    InlineEntry inline_entry = 2;
  }
}
```

A simple example of a listener collection fetch sequence:

1. Client requests `xdstp://some-authority/envoy.config.listener.v3.ListenerCollection/foo.`
2. Server responds with a list of resources: `[locator:
   xdstp://some-authority/envoy.config.listener.v3.Listener/bar, locator:
   xdstp://some-authority/envoy.config.listener.v3.Listener/baz].`
3. Client requests both
   `xdstp://some-authority/envoy.config.listener.v3.Listener/bar `and
   `xdstp://some-authority/envoy.config.listener.v3.Listener/baz.`
4. Server responds with resources contents for
   `xdstp://some-authority/envoy.config.listener.v3.Listener/bar `and
   `xdstp://some-authority/envoy.config.listener.v3.Listener/baz`.

This involves two round-trips. Inlining of resources is supported, which can reduce RTT, i.e.

1. Client requests `xdstp://some-authority/envoy.config.listener.v3.ListenerCollection/foo.`
2. Server responds with a collection of literal resources inlined in `foo`:
   `[inline_entry: xdstp://some-authority/envoy.config.listener.v3.Listener/bar,
   inline_entry: xdstp://some-authority/envoy.config.listener.v3.Listener/baz].`

Note that in all cases, the context parameters presented in the original request
must be present in the response. For example, a request for
`xdstp://some-authority/envoy.config.listener.v3.ListenerCollection/foo?some=thing`, must
be responded to with a resource named
`xdstp://some-authority/envoy.config.listener.v3.ListenerCollection/foo?some=thing`.
However, individual resources referenced by locator inside the returned list
collection do not need to have the collection-level context parameters included
in their naming.

#### Glob

Having explicit collection resources allows delta xDS to provide delta updates
on individual resources but the resource list itself can become a bottleneck for
frequently updated large collections of resources, e.g. with 1M endpoints updating
every 10s.  For this situation, we introduce *glob
collections*, which allow the `<T>Collection` directory to be elided when
resources in a collection share a directory structure and a `/*` component is appended to
the resource path. Continuing the previous example, this now looks like:

1. Client requests
   `xdstp://some-authority/envoy.config.listener.v3.Listener/foo/*`.
2. Server responds with resources
   [`xdstp://some-authority/envoy.config.listener.v3.Listener/foo/bar,
   xdstp://some-authority/envoy.config.listener.v3.Listener/foo/baz]`.

Note that there is no explicit directory sent enumerating `{bar, baz}`. Rather,
glob collections provide delta updates directly on directory resources.

Globs can exist in arbitrary path locations, e.g.
`xdstp://some-authority/envoy.config.listener.v3.Listener/some/longer/path/*`.
Multiple globs may be subscribed to in a `DeltaDiscoveryRequest`.

Since each resource returned is subject to independent update via delta xDS and
there is no explicit collection directory to update, glob collections are highly
scalable. For example, consider a collection of 10k resources and the addition
of a single resource. Glob collections will send the single additional resource
(due to the operation of delta xDS). List collections requires that the
collection directory (now containing 10001 resource references) to be sent from
server to client, as well as the additional new resource.

If no resources are present in the glob collection, the server should reply with a
`DeltaDiscoveryResponse` in which the glob collection URL is specified in
`removed_resources`.

As with list collections, context parameters in the request must be matched in
responses. A request for
`xdstp://some-authority/envoy.config.listener.v3.Listener/foo/*?some=thing` will
match a resource
`xdstp://some-authority/envoy.config.listener.v3.Listener/foo/bar?some=thing`
but not `xdstp://some-authority/envoy.config.listener.v3.Listener/foo/bar`.

#### Use cases

This proposal provides multiple collection mechanisms, as there is a need to
tradeoff ergonomics (i.e. being able to reason about a collection via single
object), performance (i.e. number of round trips) and scalability (e.e. avoiding
a collection directory becoming a bottleneck).

Some suggested use patterns for the collections are as follows:

*   Federated collections (list collections with references)
*   HTTP CDN delivery of configuration (list collections with references)
*   Handcrafted configuration on a filesystem (list collections with inline entries)
*   Migration of an existing state-of-the-world (SotW) Envoy configuration (list collections with inline entries)
*   LEDS and high scalability delta APIs (glob collections)

For any other use case with a:

*   Small collection of objects or relatively static configuration;
    list collections with inline entries are recommended. This is both
    performant and requires minimal management server state tracking and round
    trips.
*   Medium sized collection of objects; list collections with reference entries.
    The management server only needs to handle subscribe/unsubscribe state
    tracking, since both the collection and its constituent resources are
    independent xDS resources.
*   For any other use case with a large collection of objects and/or highly
    dynamic updates, glob collections are recommended. The management server needs to
    provide full delta diffs, since there is no explicit collection object to
    inform the client when resources come and go.

### Transport network addressing

An `xdstp://` URI specifies a logic authority and it’s necessary to map to some physical
network address during the resource fetch process. In the existing xDS configuration
fetch configuration, this capability is provided by a `ConfigSource` delivered alongside a
resource name in the xDS resource graph.

This proposal adds to `ConfigSource` the ability to specify the
authorities for which the `ConfigSource` may be used:

```
message Authority {
  string name = 1;

  … when signing is added, items such as CA trust chain, cert pinning …
}

message ConfigSource {
  repeated Authority authorities = N;

  …  extant ConfigSource …
}
```

When the `ConfigSource` adjacent to a resource name matches the URI authority,
the `ConfigSource` will continue to be used.

When there is no match, the xDS client will fallback to the bootstrap to map
from authority to `ConfigSource`. The bootstrap format is client specific, an
example of this is:

```
// List of authorities and config.
repeated ConfigSource xdstp_config_sources = N;

```

A client may support only static bootstrap configuration of `ConfigSource` for authority mapping. It is
expected that relevant authorities are configured in the bootstrap for referenceable servers.

To support ADS with multiple control planes, the
[`ApiType`](https://github.com/envoyproxy/envoy/blob/31128e7dc22355876020188bc8feb99304663041/api/envoy/config/core/v3/config_source.proto#L44)
enum in `ApiConfigSource` will be augmented with `AGGREGATED_DELTA_GRPC`.
This will replace and deprecate the existing `ads` field in `ConfigSource`. When
used in `xdstp://` authority resolution, an `ConfigSource` will act as an ADS
transport if configured with this new enum value. Instead of pointing to a
single shared ADS `ConfigSource` declared in the bootstrap, any resource
authority (regardless of type) that maps to a `ConfigSource` with
`AGGREGATED_DELTA_GRPC` will be multiplexed on the xDS stream specified by the
`ConfigSource`.

### Discovery request and responses

Clients are expected to have knowledge ahead of time (via mechanisms not part of
this proposal, e.g. support documentation) on whether the servers specified in
the bootstrap supports the new URI conventions.

Examples below are provided for delta xDS, but this proposal does not limit
usage to delta xDS. We directionally intend for delta xDS to supplant SotW xDS
over time, the use of inlined entries in list collections allows simple
management servers that do not wish to perform state tracking to perform
state-of-the-world updates. This is achieved by sending the entire state, e.g.
every listener inlined in a `ListenerCollection`. However, migration is
expected to be slow on the uptake and continued SotW support is provided for
this proposal.

### Server redirects

The server may issue redirects by including the following message
in a `Resource` wrapped in the `Any` message:

```
message ResourceLocator {
  string resource_locator = 1;
}
```

Redirects are only supported for
list collections. Glob collections may have individual resources redirected but the
collection itself is not redirectable.

### Examples

We provide YAML examples below of discovery request/response sequences for various use cases.

#### Singleton resource request

Client `Cluster` resource:


```
name: some-cluster
eds_cluster_config:
  service_name: xdstp://some-authority/envoy.config.endpoint.v3.ClusterLoadAssignment/foo
  eds_config:
    authorities:
    - name: some-authority
  … rest of ConfigSource pointing at xDS management server … 
```

Client EDS `DeltaDiscoveryRequest` sent to xDS management server:


```
resource_names_subscribe:
- xdstp://some-authority/envoy.config.endpoint.v3.ClusterLoadAssignment/foo
```


xDS management server `DeltaDiscoveryResponse` sent to client:


```
resources:
- version: 1
  name: xdstp://some-authority/envoy.config.endpoint.v3.ClusterLoadAssignment/foo
  resource:
    "@type": type.googleapis.com/envoy.config.endpoint.v3.ClusterLoadAssignment
    … foo's ClusterLoadAssignment payload … 
```

#### Collection resource requests

##### List collections

Client bootstrap:


```
dynamic_resources:
  lds_resources_locator:
    name: xdstp://some-authority/envoy.config.listeners.v3.ListenerCollection/foo
  lds_config:
    authorities:
    - name: some-authority
  … rest of ConfigSource pointing at xDS management server … 
```


Client LDS `DeltaDiscoveryRequest` sent to xDS management server:


```
resource_names_subscribe:
- xdstp://some-authority/envoy.config.listeners.v3.ListenerCollection/foo
```


xDS management server `DeltaDiscoveryResponse` sent to client:


```
resources:
- version: 1
  name: xdstp://some-authority/envoy.config.listeners.v3.ListenerCollection/foo
  resource:
    "@type": type.googleapis.com/envoy.config.listeners.v3.ListenerCollection
    - locator: xdstp://some-authority/envoy.config.listeners.v3.Listener/bar
    - locator: xdstp://some-authority/envoy.config.listeners.v3.Listener/baz
```


The `bar` and `baz` resources are then fetched as per [singleton resource
requests](#singleton-resource-request).

##### List collections with inlining

As with the previous list collection example, but rather than returning a list
of URLs in the response, the xDS management server sends to the
client the following `DeltaDiscoveryResponse`:


```
resources:
- version: 1
  name: xdstp://some-authority/envoy.config.listeners.v3.ListenerCollection/foo
  resource:
    "@type": type.googleapis.com/envoy.config.listeners.v3.ListenerCollection
    - inline_entry:
        name: bar
        version: 8.5.4
        resource:
          "@type": type.googleapis.com/envoy.config.listeners.v3.Listener
          … bar's ClusterLoadAssignment payload …
    - inline_entry:
        # anonymous resource
        version: 3.9.0
        resource:
          "@type": type.googleapis.com/envoy.config.listeners.v3.Listener
          … baz's ClusterLoadAssignment payload …
```


Note that the first resource bar can be referenced in a URI as
`xdstp://some-authority/envoy.config.listeners.v3.ListenerCollection/foo#entry=bar`,
while the second resource is anonymous and cannot be referenced outside the
collection.

Inlining may be used at the discretion of the management server as a transport
optimization (fewer round-trips).

##### Glob collections

Client bootstrap:


```
dynamic_resources:
  lds_resources_locator:
    name: xdstp://some-authority/envoy.config.listeners.v3.Listener/my-listeners/*?node_type=ingress
  lds_config:
    authorities:
    - name: some-authority
  … rest of ConfigSource pointing at xDS management server … 
```


Client LDS `DeltaDiscoveryRequest` sent to xDS relay proxy (note the use of client capabilities):


```
resource_names_subscribe:
- xdstp://some-authority/envoy.config.listeners.v3.Listener/my-listeners/*?node_type=ingress
```

xDS management server `DeltaDiscoveryResponse` sent to the client:


```
resources:
- version: 1
  name: xdstp://some-authority/envoy.config.listeners.v3.Listener/my-listeners/foo?node_type=ingress
  resource:
    "@type": type.googleapis.com/envoy.config.listeners.v3.Listener
    … foo's Listener payload … 
- version: 42
  name: xdstp://some-authority/envoy.config.listeners.v3.Listener/my-listeners/bar?node_type=ingress
  resource:
    "@type": type.googleapis.com/xds.core.v3.ResourceLocator
    <xdstp://some-authority/envoy.config.listeners.v3.Listener/baz>
```


In this example,
`xdstp://some-authority/envoy.config.listeners.v3.Listener/my-listeners/bar` was
redirected to `xdstp://some-authority/envoy.config.listeners.v3.Listener/baz.` The
context parameters (ingress, client caps) were used to filter down the listener
set for the client in a given collection (`my-listeners`).

#### Alternatives

In this example, a CPaaS wants to specify on-premise control plane resources as
failovers on network partition.

The CPaaS management server `DeltaDiscoveryResponse` sends to the client inside a `Cluster` resource:

```
name: some-cluster
type: EDS
eds_cluster_config:
  service_name: xdstp://some-cloud-authority/envoy.config.endpoint.v3.ClusterLoadAssignment/foo#alt=xdstp://some-onprem-authority/envoy.config.endpoint.v3.ClusterLoadAssignment/bar
  eds_config:
    authorities:
    - name: some-cloud-authority
  … rest of ConfigSource pointing at xDS management server … 
```

The client has a `ConfigSource for `some-onprem-authority` specified in its
bootstrap.

Client EDS `DeltaDiscoveryRequest` sends to xDS management server for `some-cloud-authority`:


```
resource_names_subscribe:
- xdstp://some-cloud-authority/envoy.config.endpoint.v3.ClusterLoadAssignment/foo
```

Under normal conditions, the requested resource is returned as above. If the
config source for `some-cloud-authority` is unreachable, then the client issues
a new `DeltaDiscoveryRequest` to `some-onprem-authority`:


```
resource_names_subscribe:
- xdstp://some-onprem-authority/envoy.config.endpoint.v3.ClusterLoadAssignment/bar
```

We defer to future xRFCs details on how failover, retry and recover occur.

#### xDS relay proxy

In this example, two clients work with an xDS relay proxy to receive their
configuration from some canonical xDS server.

Client A bootstrap:


```
dynamic_resources:
  lds_resources_locator:
    name: xdstp://some-authority/envoy.config.listeners.v3.Listener/a-listeners/*
  lds_config:
    authorities:
    - name: some-authority
  … rest of ConfigSource pointing at xDS relay proxy … 
```


Client A LDS `DeltaDiscoveryRequest` sent to xDS relay proxy:


```
resource_names_subscribe:
- xdstp://some-authority/envoy.config.listeners.v3.Listener/a-listeners/*
```

Client B bootstrap:


```
dynamic_resources:
  lds_resources_locator:
    name: xdstp://some-authority/envoy.config.listeners.v3.Listener/b-listeners/*
  lds_config:
    authorities:
    - mame: some-authority
  … rest of ConfigSource pointing at xDS relay proxy … 
```

Client B LDS `DiscoveryRequest` sent to xDS relay proxy:


```
resource_names_subscribe:
- xdstp://some-authority/envoy.config.listeners.v3.Listener/b-listeners/*
```


xDS relay proxy `DeltaDiscoveryRequest` sent to some `some-authority`:


```
resources_names_subscribe:
- xdstp://some-authority/envoy.config.listeners.v3.Listener/a-listeners/*
- xdstp://some-authority/envoy.config.listeners.v3.Listener/b-listeners/*
```


The origin for `some-authority` replies with a `DeltaDiscoveryResponse` sent to
xDS relay proxy:


```
resources:
- version: 1
  name: xdstp://some-authority/envoy.config.listeners.v3.Listener/a-listeners/foo
  resource:
    "@type": type.googleapis.com/envoy.config.listeners.v3.Listener
    … foo's Listener payload … 
- version: 42
  name: xdstp://some-authority/envoy.config.listeners.v3.Listener/a-listeners/bar
  resource:
    "@type": type.googleapis.com/envoy.config.listeners.v3.Listener
    … bar's Listener payload … 
- version: 13
  name: xdstp://some-authority/envoy.config.listeners.v3.Listener/b-listeners/baz
  resource:
    "@type": type.googleapis.com/envoy.config.listeners.v3.Listener
    … baz's Listener payload … 
```

xDS relay proxy `DeltaDiscoveryResponse` sent to client A:

```
resources:
- version: 1
  name: xdstp://some-authority/envoy.config.listeners.v3.Listener/a-listeners/foo
  resource:
    "@type": type.googleapis.com/envoy.config.listeners.v3.Listener
    … foo's Listener payload … 
- version: 42
  name: xdstp://some-authority/envoy.config.listeners.v3.Listener/a-listeners/bar
  resource:
    "@type": type.googleapis.com/envoy.config.listeners.v3.Listener
    … bar's Listener payload … 
```

xDS relay proxy `DeltaDiscoveryResponse` sent to client B:

```
resources:
- version: 13
  name: xdstp://some-authority/envoy.config.listeners.v3.Listener/b-listeners/baz
  resource:
    "@type": type.googleapis.com/envoy.config.listeners.v3.Listener
    … baz's Listener payload … 
```

## Rationale

N/A


## Implementation

N/A
