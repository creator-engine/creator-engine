# Versioned Egress Broker Deployment

`v1/preflight-peer-identity.sh` is the activation-time identity boundary for
the versioned egress-broker package. The broker unit runs it as `ExecStartPre`
before every activation. Its deployment env file must name the target container
and container runtime, and the target must carry the supported
`io.creator-engine.seat=<CE_EGRESS_BROKER_SEAT>` label.

```sh
deploy/egress-broker/v1/preflight-peer-identity.sh \
  --env-file /etc/creator-engine/ce-egress-broker-dev-4.env \
  --target-container <contained-seat-container>
```

The preflight reads the required seat label plus `id -u` and `id -g` inside the
supplied target container through the configured runtime. It refuses activation
when the label differs from the configured seat or when either id differs from
the expected peer UID/GID. This prevents a same-UID/GID but unrelated target
from satisfying the broker boundary. It is deliberately versioned so a later
deployment contract can be added without changing v1 semantics.

CI checks only tracked fleet structure: declared seats, broker services,
sockets, liveness services, timers, environment templates, and required broker
flags. It does not assert configured peer UID/GID values, because a checked-in
expected value is not evidence of a live target identity. The checked-in
configuration remains unverified until the activation preflight runs against
the target container.
