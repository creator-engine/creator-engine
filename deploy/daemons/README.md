# Creator Engine Daemon Containers

`run-daemon-container.sh` is the canonical host adapter for governance daemons.
It runs the daemon in the CE runtime image selected by `CE_DAEMON_IMAGE` using
the engine named by `CE_CONTAINER_ENGINE` (`docker` by default, `podman`
supported through the same OCI flags).

The runner mounts only:

- the repository checkout read-only at `CE_DAEMON_REPO_CONTAINER_PATH`
  (default `/workspace/creator-engine`);
- the daemon state root read-write at `CE_DAEMON_STATE_CONTAINER_PATH`
  (default `/ce/state`);
- the optional `CE_DAEMON_TOKEN_FILE` read-only at
  `CE_DAEMON_TOKEN_CONTAINER_PATH` (default
  `/run/creator-engine/daemon-token`).

Secrets are never baked into the image or scripts. Host bootstrap supplies
secret values at runtime through its approved environment file or through the
documented token file mount.

Queue daemon launches acquire the singleton lease named `queue-daemon` before
the queue loop starts. `CE_DAEMON_LEASE_ROOT` is a host path and must live under
`CE_DAEMON_STATE_ROOT`; the runner maps it into the container state mount. The
default host lease root is `<state root>/daemon-leases`, which maps to
`/ce/state/daemon-leases`. Use `CE_DAEMON_CONTAINER_LEASE_ROOT` only when an
explicit in-container path is required.

Lease mutation is serialized by adjacent `.lease.op.lock` files. If a host
crashes while holding an operation lock, verify no launcher or daemon process is
still running for that lease, then remove only the orphaned `.lease.op.lock`
file. Do not delete a `.lease` payload to force takeover; use the audited
takeover path with `CE_DAEMON_LEASE_TAKEOVER_REASON`.

`Dockerfile` is only a thin label layer over the canonical runtime image. Release
automation should set `CE_CANONICAL_RUNTIME_IMAGE` or `CE_DAEMON_IMAGE` to the
digest-pinned image reference governed by the release manifest.
