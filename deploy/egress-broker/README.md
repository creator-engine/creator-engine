# Versioned Egress Broker Deployment

`v1/preflight-peer-identity.sh` is the deployment-time identity boundary for
the versioned egress-broker package. An operator runs it before installing a
broker unit, with the target container name and that target's deployment env
file:

```sh
deploy/egress-broker/v1/preflight-peer-identity.sh \
  --env-file /etc/creator-engine/ce-egress-broker-dev-4.env \
  --target-container <contained-seat-container>
```

The preflight reads `id -u` and `id -g` inside the supplied target container
through `docker exec` and refuses installation when they differ from the env
file's expected peer UID/GID. It is deliberately versioned so a later
deployment contract can be added without changing v1 semantics.

CI checks only tracked fleet structure: declared seats, units, sockets,
environment templates, liveness units, and required broker flags. It does not
assert configured peer UID/GID values, because a checked-in expected value is
not evidence of a live target identity. The checked-in configuration remains
unverified until this deployment preflight is run against the target container.
