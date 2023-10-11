TP2: Dynamically Generated Cacheable xDS Resources
----
* Author(s): markdroth, htuch
* Approver: htuch
* Implemented in: <xDS client, ...>
* Last updated: 2022-02-09

## Abstract

This xRFC proposes a new mechanism to allow xDS servers to
dynamically generate the contents of xDS resources for individual
clients while at the same time preserving cacheability.  Unlike the
context parameter mechanism that is part of the new xDS naming scheme (see
[xRFC TP1](TP1-xds-transport-next.md)), the mechanism described in
this proposal is visible only to the transport protocol layer, not to the
data model layer.  This means that if a resource has a parameter that
affects its contents, that parameter is not part of the resource's name,
which means that any other resources that refer to the resource do not
need to encode the parameter.  Therefore, use of these parameters is
not viral, thus making the mechanism much easier to use.

## Background

There are many use-cases where a control plane may need to
dynamically generate the contents of xDS resources to tailor the
resources for individual clients.  One common case is where the
server has a list of routes to configure, but individual routes in
the list may be included or excluded based on the client's dynamic
selection parameters (today, conveyed as node metadata).  Thus,
the server needs to generate a slightly different version of the
`RouteConfiguration` for clients based on the parameters they send.  (See
https://cloud.google.com/traffic-director/docs/configure-advanced-traffic-management#config-filtering-metadata
for an example.)

The new xDS naming scheme described in [xRFC TP1](TP1-xds-transport-next.md)
provides a mechanism called context parameters, which is intended to move all
parameters that affect resource contents into the resource name, thus adding
cacheability to the xDS ecosystem.  However, this approach means that these
parameters become part of the resource graph on an individual client, which
causes a number of problems:
- Dynamic context parameters are viral, spreading from a given resource
  to all earlier resources in the resource graph.  For example, if
  multiple variants of an EDS resource are needed, there need to be two
  different instances of the resource with different names,
  distinguished by a context parameter.  But because the contents of the
  CDS resource include the name of the corresponding EDS resource name,
  that means that we also need two different versions of the CDS
  resource, also distinguished by the same context parameter.  And then
  we need two different versions of the RDS resource, since that needs
  to refer to the CDS resource.  And then two different versions of the
  LDS resource, which refers to the RDS resource.  This causes a
  combinatorial explosion in the number of resources needed, and it adds
  complexity to xDS servers, which need to construct the right variants
  of every resource and make sure that they refer to each other using
  the right names.
- In the new xDS naming scheme, context parameters are exact-match-only.
  This means that if a control plane wants to provide the same resource
  both with and without a given parameter, it needs to publish two
  versions of the resource, each with a different name, even though the
  contents are the same, which can also cause unnecessarily poor cache
  performance.  For example, in the "dynamic route selection" use-case,
  let's say that every client uses two different dynamic selection
  parameters, `env` (which can have one of the values `prod`, `canary`, or
  `test`) and `version` (which can have one of the values `v1`, `v2`, or
  `v3`).  Now let's say that there is a `RouteConfiguration` with one route
  that should be selected via the parameter `env=prod` and another route that
  should be selected via the parameter `version=v1`. This means that there
  are only four variants of the `RouteConfiguration` resource (`{env!=prod,
  version!=v1}`, `{env=prod, version!=v1}`, `{env!=prod, version=v1}`, and
  `{env=prod, version=v1}`).  However, the exact-match semantics means
  that there will have to be nine different versions of this resource,
  one for each combination of values of the two parameters.

### Related Proposals:
* [xRFC TP1: new xDS naming scheme](TP1-xds-transport-next.md)

## Proposal

This document proposes an alternative approach.  We start with the
observation that resource names are used in two places:

- The **transport protocol** layer, which needs to identify the right
  resource contents to send for a given resource name, often obtaining
  those resource contents from a cache.
- The **resource graph** used on an individual client, where there are a
  set of data model resources that refer to each other by name.  For
  example, a `RouteConfiguration` refers to individual `Cluster` resources
  by name.

The use-cases that we're aware of for dynamic resource selection have
an important property that we can take advantage of.  When multiple
variants of a given resource exist, any given client will only ever use
one of those variants at a given time.  That means that the parameters
that affect which variant of the resource is used are required by the
transport protocol, but they are not required by the client's data model.

It should be noted that caching xDS proxies, unlike "leaf" clients, will
need to track multiple variants of each resource, since a given caching
proxy may be serving clients that need different variants of a given
resource.  However, since caching xDS proxies deal with resources only
at the transport protocol layer, the resource graph layer is
essentially irrelevant in that case.

### Dynamic Parameters

With the above property in mind, this document proposes the following
data structures:
- **Dynamic parameters**, which are a set of key/value pairs sent by the
  client when subscribing to a resource.
- **Dynamic parameter constraints**, which are a set of criteria that
  can be used to determine whether a set of dynamic parameters matches
  the constraints.  These constraints are considered part of the unique
  identifier for an xDS resource (along with the resource name itself)
  on xDS servers, xDS clients, and xDS caching proxies.  This provides a
  mechanism to represent multiple variants of a given resource in a
  cacheable way.

Both of these data structures are used in the xDS transport protocol,
but they are not part of the resource name and therefore do not appear as
part of the resource graph.

When a client subscribes to a resource, it specifies a set of dynamic
parameters.  In response, the server will send a resource whose dynamic
parameter constraints match the dynamic parameters in the subscription
request.  A client that subscribes to multiple variants of a resource (such
as a caching xDS proxy) will use the dynamic parameter constraints on the
returned resource to determine which of its subscriptions the resource is
associated with.

Dynamic parameters, unlike context parameters, will not be
exact-match-only.  Dynamic parameter constraints will be able to represent
certain simple types of flexible matching, such as matching an exact
value or the existance of a key, and simple AND and OR combinations
of constraints.  This flexible matching semantic means that there may be
ambiguities when determining which resources match which subscriptions,
which are discussed below.

#### Constraints Representation

Dynamic parameter constraints will be represented in protobuf form as follows:

```proto
message DynamicParameterConstraints {
  // A single constraint for a given key.
  message SingleConstraint {
    message Exists {}
    // The key to match against.
    string key = 1;
    // How to match.
    oneof constraint_type {
      // Matches this exact value.
      string value = 2;
      // Key is present (matches any value except for the key being absent).
      Exists exists = 3;
    }
  }

  message ConstraintList {
    repeated DynamicParameterConstraints constraints = 1;
  }

  oneof type {
    // A single constraint to evaluate.
    SingleConstraint constraint = 1;

    // A list of constraints to be ORed together.
    ConstraintList or_constraints = 2;

    // A list of constraints to be ANDed together.
    ConstraintList and_constraints = 3;

    // The inverse (NOT) of a set of constraints.
    DynamicParameterConstraints not_constraints = 4;
  }
}
```

#### Background: xDS Client and Server Architecture

Before discussing where dynamic parameter matching is performed, it is
useful to provide some additional background on xDS client and server
architecture, independent of this design.

The xDS transport protocol is fundamentally a mechanism that matches up
subscriptions provided by a client with resources provided by a server.
The client controls what it is subscribing to at any given time,
and the server must send the resources from its database that match the
currently active subscriptions.

An xDS server may be thought of as containing a database of resources,
in which each resource has an associated list of clients that are currently
subscribed to that resource.  Whenever a client subscribes to a resource,
the server will send the current version of that resource to the client,
and it will add the client to the list of clients currently subscribed to
that resource.  Whenever the server receives a new version of that resource
in its database, it will send the update to all clients that are currently
subscribed to that resource.  Whenever a client unsubscribes from a
resource, it is removed from the list of clients subscribed to that
resource, so that the server knows not to send it subsequent updates for
that resource.

This same paradigm of matching up subscriptions with resources actually
applies to the xDS client as well.  Because the xDS transport protocol
does not require a server to resend a resource unless its contents have
changed, clients need to cache the most recently seen value locally in
case they need it again.  In general, the best way to structure an xDS
transport protocol client is as an API where the caller can start or
stop subscribing to a given resource at any time, and the xDS client will
handle the wire-level communication and cache the resources returned by
the server.  The cache in the xDS client functions very similarly to the
database in an xDS server: each cache entry contains the current value
of the resource received from the xDS server and a list of subscribers to
that resource.  When the xDS client sees the first subscription start for
a given resource, it will create the cache entry for that resource, add
the subscriber to the list of subscribers for that resource, and request
that resource from the xDS server.  When it receives the resource from
the server, it will store the resource in the cache entry and deliver
it to all subscribers.  When the xDS client sees a second subscription
start for the same resource, it will add the new subscriber to the list
of subscribers for that resource and immediately deliver the cached value
of the resource to the new subscriber.  Whenever the server sends an
updated version of the resource, the xDS client will deliver the update
to all subscribers.  When all subscriptions are stopped, the xDS client
will unsubscribe from the resource on the wire, so that the xDS server
knows to stop sending updates for that resource to the client.

In effect, the logic in an xDS client is essentially the same as that in an
xDS server, with only two differences.  First, subscriptions come from local
API callers instead of downstream RPC clients.  And second, the database does
not contain the authoritative source of the resource contents but rather cached
values obtained from the server, and the database entries are removed when
the last subscription for a given resource is stopped.

The logic in a caching xDS proxy is also essentially the same as that in an xDS
server, with only one difference.  Just like an xDS client, the database
does not contain the authoritative source of the resource contents but
rather cached values obtained from the server.  However, like an xDS
server, subscriptions do come from downstream RPC clients rather than local
API callers.

The following table summarizes this structure:

<table>

  <tr>
    <th>xDS Node Type</th>
    <th>Source of Subscriptions</th>
    <th>Source of Resource Contents</th>
  </tr>

  <tr>
    <td>xDS Server</td>
    <td>downstream xDS clients</td>
    <td>authoritative data</td>
  </tr>

  <tr>
    <td>xDS Client</td>
    <td>local API callers</td>
    <td>cached data from upstream xDS server</td>
  </tr>

  <tr>
    <td>xDS Caching Proxy</td>
    <td>downstream xDS clients</td>
    <td>cached data from upstream xDS server</td>
  </tr>

</table>

#### Where Dynamic Parameter Matching is Performed

Because of the architecture described above, evaluation of matching between
a set of dynamic parameters and a set of constraints may need to be
performed by both xDS servers and xDS clients.

xDS servers that support multiple variants of a resource perform this
matching when deciding which variant of a given resource to return for a
given subscription request.  xDS servers that support multiple variants of
a resource MUST send the dynamic parameter constraints associated with a
resource variant to the client along with that variant.  Any server
implementation that fails to do so is in violation of this specification.

xDS caching proxies that support multiple variants of a resource also
perform this matching when deciding which variant of a given resource to
return for a given subscription request.  Caching proxies MUST store the
dynamic parameter constraints obtained from the upstream server along with
each resource variant, which they will use when deciding which variant of a
given resource to return for a given subscription request from a downstream
xDS client.  Caching proxies MUST send those dynamic parameter constraints to
the downstream client when sending that variant of the resource.

Note this design assumes that a given leaf client will use a fixed set of
dynamic parameters, typically configured in a local bootstrap file, for all
subscriptions over its lifetime.  Given that, it is not strictly necessary
for a leaf client to perform this matching, since it should only ever
receive a single variant of a given resource, which should always match the
dynamic parameters it subscribed with.  However, clients MAY perform this
matching, which may be useful in cases where the same cache implementation
is used on both a leaf client and a caching proxy.

It is important to note that the dynamic parameter matching behavior becomes
an inherent part of the xDS transport protocol.  xDS servers that interact
only with leaf clients may be tempted not to send dynamic parameter
constraints to the client along with the chosen resource variant, and
leaf clients may accept that.  However, as soon as that server wants to
start interacting with a caching proxy or a client that does verify the
constraints, it will run into problems.  xDS server implementors are
strongly encouraged not to omit the dynamic parameter constraints in their
responses.

#### Example: Basic Dynamic Parameters Usage

Let's say that the clients are currently categorized by the parameter
`env`, whose value is either `prod` or `test`.  So any given client will
send one of the following sets of dynamic parameters:
- `{env=prod}`
- `{env=test}`

Now let's say that the server has two variants of a given resource, and
the variants have the following dynamic parameter constraints:

```textproto
// For {env=prod}
{constraint:{key:"env" value:"prod"}}

// For {env=test}
{constraint:{key:"env" value:"test"}}
```

When a client subscribes to this resource with dynamic parameters
`{env=prod}`, the server will return the first variant; when a client
subscribes to this resource with dynamic parameters `{env=test}`, the
server will return the second variant.  When the client receives the
returned resource, it will verify that the dynamic parameters it sent
match the constraints of the returned resource.

#### Unconstrained Parameters

Note that clients may send dynamic parameters that are not specified in
the constraints on the resulting resource.  If a set of constraints does
not specify any constraint for a given parameter sent by the client, that
parameter does not prevent the constraints from matching.  This allows
clients to add new parameters before a server begins using them.
(In general, we expect clients to send a lot of keys that may not
actually be used by the server, since deployments often divide their
clients into categories before they have a need to differentiate the
configs for those categories.)

Continuing the example above, if the server wanted to send the same
contents for a given resource to both `{env=prod}` and `{env=test}` clients,
it would have only a single variant of that resource, and that variant would
not have any constraints.  The server would therefore send that variant to
all clients, and the clients would consider it a match for the constraints
that they subscribed with.

#### Example: Transition Scenarios

Consider what happens in transition scenarios, where a deployment initially
groups its clients on a single key but then wants to add a second key.
The second key needs to be added both in the constraints on the server
side and in the clients' configurations, but those two changes cannot
occur atomically.

Let's start with the above example where the clients are already divided into
`env=prod` and `env=test`.  Let's say that now the deployment wants to add
an additional key called `version`, whose value will be either `v1` or `v2`,
so that it can further subdivide its clients' configs.

The first step is to add the new key on the clients, so that any given client
will send one of the following sets of dynamic parameters:
- `{env=prod, version=v1}`
- `{env=prod, version=v2}`
- `{env=test, version=v1}`
- `{env=test, version=v2}`

At this point, the server still does not have a variant of any resource
that has constraints for the `version` key; it has only variants that
differentiate between `env=prod` and `env=test`.  But the addition of
the new key on the clients will not affect which resource variant is
sent to each client, because it does not affect the matching.  Clients
sending `{env=prod, version=v1}` or `{env=prod, version=v2}` will both get
the resource variant for `env=prod`, and clients sending
`{env=test, version=v1}` or `{env=test, version=v2}` will both get the
resource variant for `env=test`.

Once the clients have all been updated to send the new key, then the
server can be updated to have different resource variants based on the
`version` key.  For example, it may replace the single resource variant
for `env=prod` with the following two variants:

```textproto
// For {env=prod, version=v1}
{and_constraints:[
  {constraint:{key:"env" value:"prod"}},
  {constraint:{key:"version" value:"v1"}}
]}

// For {env=prod, version=v2}
{and_constraints:[
  {constraint:{key:"env" value:"prod"}},
  {constraint:{key:"version" value:"v2"}}
]}
```

Once that change happens on the server, the clients will start getting
the correct variant of the resource based on their `version` key.

Note that in order to avoid causing matching ambiguity, the server must
handle this kind of change by sending the deletion of the original resource
variant and the creation of the replacement resource variants in a
single xDS response.  This will allow the client to atomically apply the
change to its database.  For any given subscriber, the client should
present the change as if there was only one variant of the resource and
that variant had just been updated.

#### Matching Ambiguity

As mentioned above, this design does introduce the possibility of
matching ambiguity in certain cases, where there may be more than one
variant of a resource that matches the dynamic parameters specified by
the client.

If an xDS transport protocol implementation does encounter multiple
possible matching variants of a resource, its behavior is undefined.
In the following sections, we evaluate the cases where that can occur
and specify how each one will be addressed.

##### Adding a New Key on the Server First

Consider what would happen in the above transition scenario if we changed
the server to have multiple variants of a resource differentiated by
the new `version` key before all of the clients were upgraded to use
that key.  For clients sending `{env=prod}`, there would be two possible
matching variants of the resource, one for `version=v1` and another for
`version=v2`, and there would be no way to determine which variant to
use for that client.

As stated above, we are optimizing for the case where new keys are added
on clients first, since that is expected to be the common scenario.
However, there may be cases where it is not feasible to have all clients
start sending a new key before the server needs to start making use of
that key.

For example, let's say that this transition scenario is occurring in
an environment where the xDS server is controlled by one team and the
clients are controlled by various other teams, so it's not feasible to
force all clients to start sending the new `version` key all at once.
But there is one particular client team that is eager to start using
the new `version` key to differentiate the configs of their clients,
and they don't want to wait for all of the other client teams to start
sending the new key.

Consider what happens if the server simply adds a variant of the
resource with the new key, while leaving the original resource variant
in place:

```textproto
// Existing variant for older clients that are not yet sending the
// version key.
{constraint:{key:"env" value:"prod"}}

// New variant intended for clients sending the version key.
{and_constraints:[
  {constraint:{key:"env" value:"prod"}},
  {constraint:{key:"version" value:"v1"}}
]}
```

This will work fine for older clients that are not yet sending the
`version` key, because their dynamic parameters will not match the new
variant's constraints.  However, newer clients that are sending dynamic
parameters `{env=prod, version=v1}` will run into ambiguity: those
parameters can match either of the above variants of the resource.

This situation will be avoided via a best practice that all authoritative
xDS servers should have **all variants of a given resource specify
constraints for the same set of keys**.

In order to make this work for the case where the server starts sending
the constraint on the new key before all clients are sending it, we
provide the `exists` matcher, which will allow the server to specify
a default explicitly for clients that are not yet sending a new key.
In this example, the server would actually have the following two
variants:

```textproto
// Existing variant for older clients that are not yet sending the
// version key.
{and_constraints:[
  {constraint:{key:"env" value:"prod"}},
  {not_constraint:
    {constraint:{key:"version" exists:{}}}
  }
]}

// New variant for clients sending the version key.
{and_constraints:[
  {constraint:{key:"env" value:"prod"}},
  {constraint:{key:"version" value:"v1"}}
]}
```

This allows maintaining the requirement that all variants of a given
resource have constraints on the same set of keys, while also allowing
the server to explicitly provide a result for older clients that do not
yet send the new key.

##### Variants With Overlapping Constraint Values

There is also a possible ambiguity that can occur if a server provides
multiple variants of a resource whose constraints for a given key
overlap in terms of the values they can match.  For example, let's say
that a server has the following two variants of a resource:

```textproto
// Matches {env=prod} or {env=test}.
{or_constraints:[
  {constraint:{key:"env" value:"prod"}},
  {constraint:{key:"env" value:"test"}}
]}

// Matches {env=qa} or {env=test}.
{or_constraints:[
  {constraint:{key:"env" value:"qa"}},
  {constraint:{key:"env" value:"test"}}
]}
```

Now consider what happens if a client subscribes with dynamic parameters
`{env=test}`.  Those dynamic parameters can match either of the above
variants of the resource.

This situation will be avoided via a best practice that all authoritative
xDS servers should have **all variants of a given resource specify
non-overlapping constraints for the same set of keys**.  Control planes
must not accept a set of resources that violates this requirement.

#### Matching Behavior and Best Practices

We advise deployments to avoid ambiguity through the following best practices:
- Whenever there are multiple variants of a resource, all variants must
  list the same set of keys.  This allows the server to ignore constraints
  on keys sent by the client that do not affect the choice of variant
  without causing ambiguity in cache misses.  Servers may use the
  `exists` mechanism to provide backward compatibility for clients that
  are not yet sending a newly added key.
- The constraints on each variant of a given resource must be mutually
  exclusive.  For example, if one variant of a resource matches a given key
  with values "foo" or "bar", and another variant matches that same key
  with values "bar" or "baz", that would cause ambiguity, because both
  variants would match the value "bar".
- There must be a variant of the resource for every value of a key that is
  going to be present.  For example, if clients will send constraints on the
  `env` key requiring the value to be one of `prod`, `test`, or `qa`, then
  you must have each of those three variants of the resource.  (Failure
  to do this will result in the server acting as if the requested
  resource does not exist.)

#### Transport Protocol Changes

The following message will be added to represent a subscription to a
resource by name with associated dynamic parameters:

```proto
// A specification of a resource used when subscribing or unsubscribing.
message ResourceLocator {
  // The resource name to subscribe to.
  string name = 1;

  // A set of dynamic parameters used to match against the dynamic parameter
  // constraints on the resource. This allows clients to select between
  // multiple variants of the same resource.
  map<string, string> dynamic_parameters = 2;
}
```

The following new field will be added to `DiscoveryRequest`, to allow clients
to specify dynamic parameters when subscribing to a resource:

```proto
  // Alternative to resource_names field that allows specifying cache
  // keys along with each resource name. Clients that populate this field
  // must be able to handle responses from the server where resources are
  // wrapped in a Resource message.
  repeated ResourceLocator resource_locators = 7;
```

Similarly, the following fields will be added to `DeltaDiscoveryRequest`:

```proto
  // Alternative to resource_names_subscribe field that allows specifying cache
  // keys along with each resource name.
  repeated ResourceLocator resource_locators_subscribe = 8;

  // Alternative to resource_names_unsubscribe field that allows specifying cache
  // keys along with each resource name.
  repeated ResourceLocator resource_locators_unsubscribe = 9;
```

The following message will be added to represent the name of a specific
variant of a resource:

```proto
// Specifies a concrete resource name.
message ResourceName {
  // The name of the resource.
  string name = 1;

  // Dynamic parameter constraints associated with this resource. To be used by
  // client-side caches (including xDS proxies) when matching subscribed
  // resource locators.
  DynamicParameterConstraints dynamic_parameter_constraints = 2;
}
```

The following field will be added to the `Resource` message, to allow the
server to return the dynamic parameters associated with each resource:

```proto
  // Alternative to the *name* field, to be used when the server supports
  // multiple variants of the named resource that are differentiated by
  // dynamic parameter constraints.
  // Only one of *name* or *resource_name* may be set.
  ResourceName resource_name = 8;
```

And finally, the following field will be added to `DeltaDiscoveryResponse`:

```proto
  // Alternative to removed_resources that allows specifying which variant of
  // a resource is being removed. This variant must be used for any resource
  // for which dynamic parameter constraints were sent to the client.
  repeated ResourceName removed_resource_names = 8;
```

### Client Configuration

Client configuration is outside of the scope of this design.  However,
this section lists some considerations for client implementors to take
into account.

#### Configuring Dynamic Parameters

Each leaf client should have a way of configuring the dynamic parameters
that it sends.

For old-style resource names (those not using the new `xdstp` URI
scheme from [xRFC TP1](TP1-xds-transport-next.md)), clients should
send the same set of dynamic parameters for all resource subscriptions.
The client's configuration should allow setting these default dynamic
parameters globally.

For new-style resource names, clients should send the same set of
dynamic parameters for all resource subscriptions in a given authority.
The client's configuration should allow setting the dymamic parameters to
use for each authority.

#### Migrating From Node Metadata

Today, the equivalent of dynamic parameter constraints is node metadata,
which can be used by servers to determine the set of resources to send
for LDS and CDS wildcard subscriptions or to determine the contents of
other resources (e.g., to select individual routes to be included in an
RDS resource).  For transition purposes, this mechanism can continue
to be supported by the client performing direct translation of node
metadata to dynamic parameters.

Any given xDS client may support either or both of these mechanisms.

### Considerations for Implementations

This specification does not prescribe implementation details for xDS
clients or servers.  However, for illustration purposes, this section
describes how a naive implementation might be structured.

The database of an xDS server or cache of an xDS client can be thought
of as a map, keyed by resource type and resource name.  Prior to this
specification, the value of the map would have been the current value of the
resource and a list of subscribers that need to be updated when the
resource changes.  In C++ syntax, the data structure might look like this:

```c++
// Represents a subscriber (either a downstream xDS client or a local API caller).
class Subscriber {
 public:
  // ...
};

struct DatabaseEntry {
  // Current contents of resource.
  // Whenever this changes, the change will be sent to all subscribers.
  std::optional<google::protobuf::Any> resource_contents;

  // Current list of subscribers.
  // Entries are added and removed as subscriptions are started and stopped.
  std::set<Subscriber*> subscribers;
};

using Database =
    std::map<std::string /*resource_type*/,
             std::map<std::string /*resource_name*/, DatabaseEntry>;
```

This design does not change the key structure of the map, but it does
change the structure of the value of the map.  In particular, instead of
storing a single value for the resource contents, it will need to store
multiple values, keyed by the associated dynamic parameter constraints.
And for each subscriber, it will need to store the dynamic parameters that
the subscriber specified.  In a naive implementation (not optimized at all),
the modified data structure may look like this:

```c++
// Represents a subscriber (either a downstream xDS client or a local API caller).
class Subscriber {
 public:
  // ...

  // Returns the dynamic parameters specified for the subscription.
  DynamicParameters dynamic_parameters() const;
};

struct DatabaseEntry {
  // Resource contents for each variant of the resource, keyed by
  // dynamic parameter constraints.
  // Whenever a given variant of the resource changes, the change will be
  // sent to all subscribers whose dynamic parameters match the constraints
  // of the resource variant that changed.
  std::map<DynamicParameterConstraints,
           std::optional<google::protobuf::Any>> resource_contents;

  // Current list of subscribers.
  // Entries are added and removed as subscriptions are started and stopped.
  std::set<Subscriber*> subscribers;
};
```

When a variant of a resource is updated, the variant is stored in the map
based on its dynamic parameter constraints.  The implementation will then
iterate through the list of subscribers, sending the updated resource
variant and its dynamic parameter constraints to each subscriber whose
dynamic parameters match those constraints.

A more optimized implementation may instead choose to store a separate list
of subscribers for each resource variant, thus avoiding the need to perform
matching for every subscriber upon every update of a resource variant.
However, this would require moving subscribers from one variant to another
whenever the dynamic parameters change on the resource variants.

### Example

This section shows how the mechanism described in this proposal can be
used to address the use-case described in the "Background" section above.

Let's say that every client uses two different dynamic selection
parameters, `env` (which can have one of the values `prod`, `canary`,
or `test`) and `version` (which can have one of the values `v1`, `v2`,
or `v3`).  Now let's say that there is a `RouteConfiguration` with one
route that should be selected via the parameter `env=prod` and another
route that should be selected via the parameter `version=v1`. Without
this design, the server would need to actually provide the cross-product
of these parameter values, so there will be 9 different variants of the
resource, even though there are only 4 unique contents for the resource.
However, this design instead allows the server to provide only the 4
unique variants of the resource, with constraints allowing each client
to get the appropriate one:

<table>
  <tr>
    <th>Dynamic Parameter Constraints on Resource</th>
    <th>Resource Contents</th>
  </tr>

  <tr>
    <td>
<code>{and_constraints:[
  {not_constraints:
    {constraint:{key:"env" value:"prod"}}
  },
  {not_constraints:
    {constraint:{key:"version" value:"v1"}}
  }
]}</code>
    </td>
    <td>
      <ul>
      <li>does <i>not</i> include the route for <code>env=prod</code>
      <li>does <i>not</i> include the route for <code>version=v1</code>
      </ul>
    </td>
  </tr>

  <tr>
    <td>
<code>{and_constraints:[
  {constraint:{key:"env" value:"prod"}},
  {not_constraints:
    {constraint:{key:"version" value:"v1"}
  }
]}</code>
    </td>
    <td>
      <ul>
      <li>does include the route for <code>env=prod</code>
      <li>does <i>not</i> include the route for <code>version=v1</code>
      </ul>
    </td>
  </tr>

  <tr>
    <td>
<code>{and_constraints:[
  {not_constraints:
    {constraint:{key:"env" value:"prod"}}
  },
  {constraint:{key:"version" value:"v1"}}
]}</code>
    </td>
    <td>
      <ul>
      <li>does <i>not</i> include the route for <code>env=prod</code>
      <li>does include the route for <code>version=v1</code>
      </ul>
    </td>
  </tr>

  <tr>
    <td>
<code>{and_constraints:[
  {constraint:{key:"env" value:"prod"}},
  {constraint:{key:"version" value:"v1"}}
]}</code>
    </td>
    <td>
      <ul>
      <li>does include the route for <code>env=prod</code>
      <li>does include the route for <code>version=v1</code>
      </ul>
    </td>
  </tr>

</table>

## Rationale

This section documents limitations and design alternatives that we
considered.

### Limitation on Enhancing Matching in the Future

One limitation of this design is that, because all xDS transport protocol
implementations (clients, servers, and caching proxies) need to implement
this matching behavior, it will be very difficult to add new matching
behavior in the future.  Doing so will probably require some sort of
client capability.  This will make it feasible to expand this mechanism
in an environment where all of the caching xDS proxies are under centralized
control, but it will be quite difficult to deploy those changes in
environments that depend on distributed third-party caching xDS proxies.

Because of this, reviewers of this design are encouraged to carefully
scrutinize the proposed matching semantics to ensure that they meet our
expected needs.

### Complexity of Constraint Expressions

Although the `DynamicParameterConstraints` proto allows specifying
arbitrarily nested combinations of AND, OR, and NOT expressions, control
planes do not need to actually support that full arbitrary power.  It is
possible to limit the sets of supported constraints to (e.g.) a
simple flat list of AND or OR expressions, which would make it easier
for a control plane to optimize its implementation.

Simimarly, caching xDS proxies may be able to provide an optimized
implementation if all of the constraints that they see are limited to
some subset of the full flexibility allowed by the protocol.  However,
any general-purpose caching proxy implementation will likely need to
support a less optimized implementation that does support the full
flexibility allowed by the protocol.

### Using Context Parameters

We considered extending the context parameter mechanism from [xRFC
TP1](TP1-xds-transport-next.md) to support flexible matching semantics,
rather that its current exact-match semantics.  However, that approach had
some down-sides:
- It would not have solved the virality problem described in the "Background"
  section above.
- It would have made the new xDS naming scheme a prerequisite for using
  the dynamic resource selection mechanism.  (The mechanism described in
  this doc is completely independent of the new xDS naming scheme; it can
  be used with the legacy xDS naming scheme as well.)

### Stricter Matching to Avoid Ambiguity

We could avoid much of the matching ambiguity described above by saying that
a set of constraints must specify all keys present in the subscription
request in order to match.  However, this would mean that if the client
starts subscribing with a new key before the corresponding constraint is
added on the resources on the server, then it will fail to match the
existing resources.  In other words, the process would be:

1. Add a variant of all resources on the server side with a constraint
   for `version=v1` (in addition to all existing constraints).
2. Change clients to start sending the new key.
3. When all clients are updated, remove the resource variants that do
   *not* have the new key.

This will effectively require adding new keys on the server side first,
which seems like a large burden on users.  It also seems fairly tricky
for most users to get the exactly correct set of dynamic parameters on
each resource variant, and if they fail to do it right, they will break
their existing configuration.

Ultimately, although this approach is more semantically precise, it is
also considered too rigid and difficult for users to work with.

## Implementation

TBD (Will probably be implemented in gRPC before Envoy)

## Open issues (if applicable)

N/A
