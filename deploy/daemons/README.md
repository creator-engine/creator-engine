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

## UID And Ownership Contract

Daemon containers run as the canonical runtime image uid/gid. Set
`CE_DAEMON_IMAGE_UID` only when the runtime image declares a different uid/gid;
the default is `10001`.

For Docker, host-mounted daemon state must be owned by that image uid because the
container process is non-root. On first boot the runner creates missing state
roots when it can, but an existing root owned by another uid is refused with a
copy-pasteable remediation:

```sh
chown -R <uid>:<uid> <state_root>
```

For the default image this is:

```sh
chown -R 10001:10001 <state_root>
```

The runner verifies mode `0700` and does not chmod or chown existing state
directories implicitly.

Lease mutation is serialized by adjacent `.lease.op.lock` files. If a host
crashes while holding an operation lock, verify no launcher or daemon process is
still running for that lease, then remove only the orphaned `.lease.op.lock`
file. Do not delete a `.lease` payload to force takeover; use the audited
takeover path with `CE_DAEMON_LEASE_TAKEOVER_REASON`.

`Dockerfile` is only a thin label layer over the canonical runtime image. Release
automation should set `CE_CANONICAL_RUNTIME_IMAGE` or `CE_DAEMON_IMAGE` to the
digest-pinned image reference governed by the release manifest.

`smoke-daemon-container.sh <scratch-state-root>` is a host-operator smoke that
runs the conveyor-daemon container twice against one scratch state root and
verifies lease release/reacquisition, Docker uid ownership, and that no
signing-secret content persists onto host state after stop; run it before
cutting over a host from the uncontained daemon to the containerized adapter.
