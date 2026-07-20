---
slug: ce623-egress-broker-parity
date: 2026-07-20
kind: changed
scope: egress-broker
issue: ce-ops#623
work_class: story
---

**Add versioned fleet egress-broker deployment parity.**

The shipped deployment metadata covers the dev-3/dev-4 rollout set. Dev-4 is
pinned to `/run/ce-egress/dev-4.sock`, the `ce-dev-4` socket group, and
configured expected `SO_PEERCRED` UID/GID `1008`/`1008`. Dev-3 deliberately
uses the host-local `<set-at-deployment>` UID/GID placeholder, so no private
identity is duplicated in checked-in metadata.

`deploy/egress-broker/v1/preflight-peer-identity.sh` is the deployment-time
boundary: before installation, it reads `id -u` and `id -g` from the named
target container and refuses a configured peer identity mismatch. Its focused
test uses a controlled container-runtime fixture only; it neither inspects a
live container nor proves a host deployment.

The dev-3 and dev-4 services route terminal failures to their shared liveness
service/timer pattern. Each check runs `systemctl is-active`, records the
observed state through `systemd-cat`, and fails unless the broker unit is
active. This makes missing deployed units and start-limit crash loops observable
through the journal and timer result.

These metadata and fixture checks do not deploy, enable, start, inspect, or
restart any host service. Operators remain responsible for running preflight and
verifying installation, socket mounting, and live broker authentication.
