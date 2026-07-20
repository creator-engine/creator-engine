---
slug: ce623-egress-broker-parity
date: 2026-07-20
kind: changed
scope: egress-broker
issue: ce-ops#623
work_class: story
---

**Add versioned dev-4 egress-broker deployment parity.**

The versioned dev-4 package supplies the broker environment template, a
single-seat broker configuration, and matching systemd service/socket units.
The broker is pinned to `/run/ce-egress/dev-4.sock`, the `ce-dev-4` socket
group, and expected `SO_PEERCRED` UID/GID `1004`/`1004`.

`deploy/egress-broker/fleet-seats.json` declares the dev-3/dev-4 broker rollout
set and cites the existing broker app table as its seat source. The focused
static test requires every declared seat to retain a complete tracked
unit-to-socket push path, and requires dev-4's environment and broker JSON to
match the service/socket identity exactly.

The dev-4 service has a bounded restart policy and routes terminal failures to
a liveness check. The liveness timer checks `systemctl is-active`, emits the
observed state through `systemd-cat`, and exits nonzero unless the unit is
active. This makes a missing unit after deployment or a crash loop that reaches
the start limit observable in the journal and timer result.

These files do not deploy, enable, start, inspect, or restart any host service.
They cannot prove that the environment/config files were installed at their
target paths, that the socket is mounted into a container, that the configured
peer is uid/gid 1004, or that a live broker can authenticate and push. Those
are operator-owned runtime deployment checks.
