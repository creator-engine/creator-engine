---
slug: ce623-egress-broker-parity
date: 2026-07-20
kind: changed
scope: egress-broker
issue: ce-ops#623
work_class: story
---

**Add versioned fleet egress-broker deployment parity.**

The versioned package supplies broker environment templates, a single-seat
dev-4 broker configuration, and matching systemd service/socket units for
every declared fleet seat.
The broker is pinned to `/run/ce-egress/dev-4.sock`, the `ce-dev-4` socket
group, and configured expected `SO_PEERCRED` UID/GID `1008`/`1008`.

`deploy/egress-broker/fleet-seats.json` declares the dev-3/dev-4 broker rollout
set and cites the existing broker app table as its seat source. The focused
static test requires every declared seat to retain a complete tracked service,
socket, environment template, and liveness path, required broker flags, and no
broker service without a fleet entry. It deliberately does not compare any
configured peer UID/GID with a checked-in expected value.

The dev-4 service has a bounded restart policy and routes terminal failures to
a liveness check. The liveness timer checks `systemctl is-active`, emits the
observed state through `systemd-cat`, and exits nonzero unless the unit is
active. This makes a missing unit after deployment or a crash loop that reaches
the start limit observable in the journal and timer result.

`deploy/egress-broker/v1/preflight-peer-identity.sh` is the deployment-time
boundary: before installation, it reads `id -u` and `id -g` from the named
target container and refuses a configured peer identity mismatch. Its focused
test uses a controlled container-runtime fixture only; this change does not
inspect a live container or runtime.

A CI peer-ID assertion would be theatre: it could only compare a checked-in
value with another checked-in value, not prove target identity. The checked-in
dev-4 value remains unverified until the deployment preflight runs. These files
do not deploy, enable, start, inspect, or restart any host service. They cannot
prove that the environment/config files were installed at their target paths,
that the socket is mounted into a container, or that a live broker can
authenticate and push. Those are operator-owned runtime deployment checks.
