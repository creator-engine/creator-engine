# Queue Daemon Declaration

This directory declares the queue-daemon singleton topology. The approved
redeploy command renders `ce-queue-daemon.service` before installation. Its
checked-in repository root, service account, and environment-file values are
renderer parameters, not deployment identity. The environment template uses
these placeholders:

- `@REPO_ROOT@`: checked-out repository root.
- `@STATE_ROOT@`: persistent state root mounted into the container.
- `@CONTAINER_ENGINE@`, `@DAEMON_IMAGE@`, and `@DAEMON_IMAGE_UID@`: approved
  container runtime values.

The service waits for `network-online.target` before it starts. The daemon runs
in the deployment host's container runtime and preserves that host's network
reachability. It restarts continuously and retains the hardening directives
`NoNewPrivileges`, `PrivateTmp`, and `ProtectSystem`.

`ce-queue-daemon.env.template` is the environment-file shape. Populate secret
placeholders only through the approved deployment channel. The liveness state
path is deliberately an in-container path under the mounted state volume.

Redeploy the declared singleton with:

```sh
deploy/singleton-redeploy/redeploy-singleton.sh --daemon queue-daemon
```
