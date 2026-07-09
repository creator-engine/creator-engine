# Queue Daemon Relocation Runbook

This runbook installs the merge-queue daemon as a singleton systemd service on a
chosen deployment host. The systemd unit is a host bootstrap adapter: it starts
`deploy/daemons/run-daemon-container.sh queue-daemon` and lets the daemon
container own the long-running process.

Use placeholders in tickets and evidence:

- `<deploy-host>`: the host receiving the service.
- `<repo-root>`: checked-out Creator Engine repository path.
- `<service-user>`: local account that owns and runs the service.
- `<env-file>`: host-local secret env file, usually
  `/etc/creator-engine/ce-queue-daemon.env`.
- `<state-root>`: persistent daemon state directory, usually
  `/var/lib/ce-queue-daemon`.

## Files

- `ce-queue-daemon.service`: thin system service with `Restart=always`,
  journald logging, start-limit protection, and `WantedBy=multi-user.target`.
- `deploy/singleton-redeploy/redeploy-singleton.sh`: renders the unit for the
  local `<repo-root>`, `<env-file>`, and `<service-user>`, then reloads and
  starts the service.
- `deploy/daemons/run-daemon-container.sh`: Docker/Podman runner. It mounts the
  checkout read-only, the daemon state root read-write, and optional token/CA
  files read-only.
- `launch-queue-daemon.sh`: fail-closed direct launcher for `cev3 queue-daemon`
  with a `--health` mode. Setting `CE_DAEMON_UNCONTAINED=1` keeps the legacy
  direct host path available as an explicit rollback escape hatch.
- `<env-file>`: host-local secret environment file. Do not commit this file or
  its values.

## Prerequisites

1. Pick one active host. Stop any previous queue-daemon process before starting
   the systemd service on the new host:

   ```bash
   pkill -f 'queue-daemon.*--loop' || true
   ```

2. Prepare the checkout and service account on `<deploy-host>`:

   ```bash
   sudo install -d -m 0755 /etc/creator-engine
   sudo install -d -m 0755 -o <service-user> -g <service-user> <repo-root>
   ```

3. Create `<env-file>` from the approved secret channel. Use variable names only
   in tickets/logs; never paste token values.

   ```bash
   sudo install -m 0600 -o root -g root /dev/null <env-file>
   sudoedit <env-file>
   ```

   Env file template:

   ```text
   GH_TOKEN=<overwatch-integrator-token>
   BAO_TOKEN=<least-privilege-openbao-daemon-token>
   BAO_ADDR=https://<openbao-host>:8200
   BAO_CACERT=<optional-host-ca-cert-path>
   CE_GATE_REPO=creator-engine/creator-engine
   CE_GATE_AUTHORIZED_REVIEWERS=<authorized-reviewer-login[,login...]>
   CE_OPENBAO_KV_MOUNT=ce-kv
   CE_APPROVAL_WALL_SECRET_PATH=forge/approval-capability/wall
   CE_APPROVAL_WALL_SECRET_FIELD=signing_secret
   CE_APPROVAL_WALL_POLICY_SHA=<approval-policy-sha-or-id>
   CE_APPROVAL_WALL_SECRET_REF_POLICY_SHA=<approval-wall-secret-ref-policy-sha-or-id>
   ```

   Optional container/runtime settings:

   ```text
   CE_CONTAINER_ENGINE=docker
   CE_DAEMON_IMAGE=ghcr.io/creator-engine/creator-engine/ce-runtime:<tag-or-digest>
   CE_DAEMON_LEASE_ROOT=<state-root>/daemon-leases
   CE_DAEMON_TOKEN_FILE=<approved-runtime-token-file>
   CE_DAEMON_CACERT_FILE=<host-ca-cert-file>
   ```

   `BAO_CACERT` is consumed by both the host health probe and the daemon
   launcher. For contained runs, prefer `CE_DAEMON_CACERT_FILE=<host-ca-cert>`
   when the CA file must be mounted into the container; the runner maps it to the
   in-container `BAO_CACERT` path automatically.

   Systemd applies the service `EnvironmentFile=` first, then later
   `Environment=` assignments from the unit and drop-ins. When the same variable
   is assigned more than once, the last assignment wins, so keep host-specific
   OpenBao addresses in `<env-file>` unless an intentional drop-in override is
   required.

## Install Or Redeploy

Run the singleton redeploy script from the checkout that should back the
service:

```bash
cd <repo-root>
deploy/singleton-redeploy/redeploy-singleton.sh \
  --daemon queue-daemon \
  --repo-root <repo-root> \
  --env-file <env-file> \
  --service-user <service-user>
```

Dry-run first when changing hosts or state layout:

```bash
deploy/singleton-redeploy/redeploy-singleton.sh \
  --daemon queue-daemon \
  --repo-root <repo-root> \
  --env-file <env-file> \
  --service-user <service-user> \
  --dry-run
```

The redeploy script accepts normal clones and linked Git worktrees. The daemon
container mounts `<repo-root>` read-only, so the deployment surface only needs
the checked-out files under that root. If future daemon logic needs Git metadata
inside the container, use a standalone clone or mount the worktree gitdir
explicitly before enabling that behavior.

## State Root Override

The committed unit defaults to `/var/lib/ce-queue-daemon`. Override the state
root with a systemd drop-in when a host needs a different disk:

```bash
sudo systemctl edit ce-queue-daemon.service
```

Drop-in example:

```ini
[Service]
Environment=CE_DAEMON_STATE_ROOT=<state-root>
Environment=CE_DAEMON_LEASE_ROOT=<state-root>/daemon-leases
Environment=CE_APPROVAL_WALL_STATE=<state-root>/approval-wall-state.json
Environment=CE_APPROVAL_WALL_SECRET_TARGET_FILE=/run/ce-queue-daemon/approval-wall-secret
```

Then reload and redeploy:

```bash
sudo systemctl daemon-reload
deploy/singleton-redeploy/redeploy-singleton.sh \
  --daemon queue-daemon \
  --repo-root <repo-root> \
  --env-file <env-file> \
  --service-user <service-user>
```

## Verification

```bash
sudo systemd-analyze verify /etc/systemd/system/ce-queue-daemon.service
sudo systemctl status ce-queue-daemon.service
sudo <repo-root>/deploy/queue-daemon/launch-queue-daemon.sh --health
journalctl -u ce-queue-daemon.service -n 100 --no-pager
```

If `systemd-analyze` is unavailable in a container, run the verify command on
`<deploy-host>` before enabling the service.

Verify approval auto-merge behavior with a controlled test PR:

- Open a low-risk PR against `creator-engine/creator-engine`.
- Wait for required checks to go green.
- Have an authorized non-author reviewer approve the current head SHA.
- Confirm the daemon emits a queue/enqueue decision in journald and the PR
  auto-merges through the merge queue.
- Confirm no previous `queue-daemon --loop` process is running on any other
  host.

## VPS Example

For a small always-on VPS:

```bash
<repo-root>=/workspace/creator-engine
<service-user>=ce-service
<env-file>=/etc/creator-engine/ce-queue-daemon.env
<state-root>=/var/lib/ce-queue-daemon
```

Use the default state root unless the VPS has a separate persistent data volume.
Set `CE_CONTAINER_ENGINE=docker` or `podman` in `<env-file>` to match the host.

## GPU Host Example

For a GPU or lab host used as a fallback:

```bash
<repo-root>=/srv/creator-engine
<service-user>=ce-service
<env-file>=/etc/creator-engine/ce-queue-daemon.env
<state-root>=/mnt/ce-state/queue-daemon
```

Install the state-root drop-in before redeploying. Keep the same singleton rule:
only one queue daemon may be active across the VPS and GPU-host examples.

## Rollback

Rollback is a host move, not permission to run a duplicate daemon.

1. Stop the current service:

   ```bash
   sudo systemctl disable --now ce-queue-daemon.service
   sudo systemctl status ce-queue-daemon.service
   ```

2. Redeploy on the fallback host with that host's `<repo-root>`,
   `<service-user>`, `<env-file>`, and optional state-root drop-in.

3. If the container path is unavailable and a temporary direct host launch is
   required, add this line to `<env-file>` before redeploying:

   ```text
   CE_DAEMON_UNCONTAINED=1
   ```

4. Confirm exactly one daemon is active across all hosts:

   ```bash
   pgrep -af 'queue-daemon.*--loop'
   ```

## Lease Recovery

The queue loop is singleton-gated by the filesystem lease named
`queue-daemon`. `CE_DAEMON_LEASE_ROOT` is a host path and must stay under
`CE_DAEMON_STATE_ROOT` unless `CE_DAEMON_CONTAINER_LEASE_ROOT` is set for an
explicit in-container override.

Lease recovery is manual and fail-closed. If the queue daemon refuses to start
because `queue-daemon.lease` is already present, verify no launcher or daemon
process is still running for that lease before removing the stale lease file. If
only `queue-daemon.lease.op.lock` remains after a host crash, verify no lease
operation is still active, then remove only the orphaned operation-lock file.
Never remove a live lease to start a second queue daemon.
