# Queue Daemon Relocation Runbook

This package moves the merge-queue daemon from an ad-hoc DGX launch into the
canonical daemon container. The systemd unit is only a host bootstrap adapter:
it starts `deploy/daemons/run-daemon-container.sh queue-daemon` and lets the
container runtime own the daemon process.

## Files

- `ce-queue-daemon.service`: thin system service with `Restart=always`,
  `RestartSec=5`, journald logging, start-limit protection, and
  `WantedBy=multi-user.target`. By default it invokes the contained daemon
  runner.
- `deploy/daemons/run-daemon-container.sh`: engine-agnostic Docker/Podman runner
  for daemon containers. It mounts the checkout read-only, the daemon state root
  read-write, and an optional token file read-only.
- `launch-queue-daemon.sh`: fail-closed direct launcher for `cev3 queue-daemon`
  with a `--health` mode. Default start delegates to the container runner;
  setting `CE_DAEMON_UNCONTAINED=1` keeps the legacy direct host path available
  as an explicit escape hatch.
- `/etc/creator-engine/ce-queue-daemon.env`: host-local secret environment file.
  Do not commit this file or its values.

## CE-DEV-1 VPS Cutover

1. Stop the DGX ad-hoc daemon so only one integrator can enqueue merges:

   ```bash
   pkill -f 'queue-daemon.*--loop' || true
   ```

2. On CE-DEV-1, install from the approved checkout as the dev-1 service user.
   The commands below assume `/workspace/creator-engine` and the service account
   `ce-dev-1`; adjust only if the live host uses a different checked-out path or
   account name.

   ```bash
   sudo install -d -m 0755 /etc/creator-engine
   sudo install -d -m 0755 /workspace/creator-engine/deploy/daemons
   sudo install -m 0644 deploy/queue-daemon/ce-queue-daemon.service /etc/systemd/system/ce-queue-daemon.service
   sudo install -m 0755 deploy/daemons/run-daemon-container.sh /workspace/creator-engine/deploy/daemons/run-daemon-container.sh
   sudo install -m 0755 deploy/queue-daemon/launch-queue-daemon.sh /workspace/creator-engine/deploy/queue-daemon/launch-queue-daemon.sh
   ```

3. Create `/etc/creator-engine/ce-queue-daemon.env` from the approved secret
   channel. Use variable names only in tickets/logs; never paste token values.

   ```bash
   sudo install -m 0600 -o root -g root /dev/null /etc/creator-engine/ce-queue-daemon.env
   sudoedit /etc/creator-engine/ce-queue-daemon.env
   ```

   Required keys:

   ```text
   GH_TOKEN=<overwatch-integrator-token>
   BAO_TOKEN=<least-privilege-openbao-daemon-token>
   BAO_CACERT=<optional-ca-cert-path>
   CE_GATE_REPO=creator-engine/creator-engine
   CE_GATE_AUTHORIZED_REVIEWERS=<authorized-reviewer-login[,login...]>
   CE_OPENBAO_KV_MOUNT=ce-kv
   CE_APPROVAL_WALL_SECRET_PATH=forge/approval-capability/wall
   CE_APPROVAL_WALL_SECRET_FIELD=signing_secret
   CE_APPROVAL_WALL_POLICY_SHA=<approval-policy-sha-or-id>
   CE_APPROVAL_WALL_SECRET_REF_POLICY_SHA=<approval-wall-secret-ref-policy-sha-or-id>
   ```

   The unit pins `BAO_ADDR=https://100.72.252.20:8200`, and sets runtime/state
   paths under `/run/ce-queue-daemon` and `/var/lib/ce-queue-daemon`. The
   contained path maps `/var/lib/ce-queue-daemon` to `/ce/state` inside the
   container. Optional container settings:

   ```text
   CE_CONTAINER_ENGINE=docker
   CE_DAEMON_IMAGE=creator-engine/ce-validator:0.3.1
   CE_DAEMON_LEASE_ROOT=/var/lib/ce-queue-daemon/daemon-leases
   CE_DAEMON_TOKEN_FILE=/approved/runtime/token-file
   ```

   Use a digest-pinned `CE_DAEMON_IMAGE` when release automation publishes the
   canonical runtime image digest.

   The queue loop is singleton-gated by the filesystem lease named
   `queue-daemon`. `CE_DAEMON_LEASE_ROOT` is a host path and must stay under the
   host `CE_DAEMON_STATE_ROOT` (`/var/lib/ce-queue-daemon` in this unit). The
   container runner maps that host lease root to the corresponding path under
   `/ce/state`; the default host path
   `/var/lib/ce-queue-daemon/daemon-leases` becomes
   `/ce/state/daemon-leases` inside the container. Use
   `CE_DAEMON_CONTAINER_LEASE_ROOT` only for an explicit in-container override.
   The `CE_DAEMON_UNCONTAINED=1` rollback path still acquires the same lease; it
   is an old launch method, not permission to run a duplicate live daemon.

   Lease recovery is manual and fail-closed. If the queue daemon refuses to
   start because `queue-daemon.lease` is already present, verify no launcher or
   daemon process is still running for that lease before removing the stale
   lease file. If only `queue-daemon.lease.op.lock` remains after a host crash,
   verify no lease operation is still active, then remove only the orphaned
   operation-lock file. Never remove a live lease to start a second queue
   daemon.

   The lease has two cooperating levels, not two competing ones. The launcher
   (`launch-queue-daemon.sh`, in both the host and container form) is itself a
   long-lived supervisor process: it acquires the `queue-daemon` lease first,
   then starts the daemon process as its own child and heartbeats the lease
   for as long as that child is alive. The daemon process, when it finds the
   lease already held by a live process that is verifiably recorded on this
   same host AND is an ancestor of the current process, defers to the
   supervisor's lease instead of trying to acquire a second one — the
   supervisor's held lease already is the singleton enforcement, so the
   daemon proceeds straight into its normal startup. The host-equality check
   is a strict precondition of the ancestry walk: pid namespaces are
   host-local, so a remote-host lease record (even one with a pid that
   numerically collides with a real local ancestor such as the container init
   process at pid 1) is never eligible for deferral and is refused exactly as
   any other unrelated live holder. If the daemon is instead invoked directly
   (no supervisor in its process ancestry — for example a manual foreground
   run for debugging), it acquires the lease itself exactly as it always has.
   Any lease held by a process that is not a same-host verified ancestor is
   refused, and a stale lease (holder process dead, or TTL-expired for a
   remote host) is refused exactly as before regardless of any ancestry —
   deferral only ever applies to a live, same-host, verified ancestor holder.

4. Verify and start:

   ```bash
   sudo systemd-analyze verify /etc/systemd/system/ce-queue-daemon.service
   sudo systemctl daemon-reload
   sudo systemctl enable --now ce-queue-daemon.service
   sudo systemctl status ce-queue-daemon.service
   sudo /workspace/creator-engine/deploy/queue-daemon/launch-queue-daemon.sh --health
   journalctl -u ce-queue-daemon.service -n 100 --no-pager
   ```

   If `systemd-analyze` is unavailable in a container, run the verify command on
   CE-DEV-1 before enabling the service.

5. Verify approval auto-merge behavior with a controlled test PR:

   - Open a low-risk PR against `creator-engine/creator-engine`.
   - Wait for required checks to go green.
   - Have an authorized non-author reviewer approve the current head SHA.
   - Confirm the VPS daemon emits a queue/enqueue decision in journald and the PR
     auto-merges through the merge queue.
   - Confirm no DGX `queue-daemon --loop` process is running.

6. Retire the DGX ad-hoc launcher after the VPS proof:

   ```bash
   pkill -f 'queue-daemon.*--loop' || true
   test ! -x "$HOME/ce-wall-daemon-launch.sh" || chmod 000 "$HOME/ce-wall-daemon-launch.sh"
   ```

   Record the VPS service status, health output, and test PR URL in the cutover
   evidence.

## Rollback To DGX

Use rollback if the VPS service misbehaves, cannot validate tokens, or fails to
enqueue the controlled test PR.

1. Stop the VPS service:

   ```bash
   sudo systemctl disable --now ce-queue-daemon.service
   sudo systemctl status ce-queue-daemon.service
   ```

2. Reinstall the same committed unit on DGX, or restart the existing DGX
   launcher only as a temporary bridge. Prefer the committed unit because
   `Restart=always` and boot persistence apply on DGX too. To use the legacy
   direct host launch path temporarily, add this line to
   `/etc/creator-engine/ce-queue-daemon.env`:

   ```text
   CE_DAEMON_UNCONTAINED=1
   ```

   ```bash
   sudo install -d -m 0755 /etc/creator-engine
   sudo install -d -m 0755 /workspace/creator-engine/deploy/daemons
   sudo install -m 0644 deploy/queue-daemon/ce-queue-daemon.service /etc/systemd/system/ce-queue-daemon.service
   sudo install -m 0755 deploy/daemons/run-daemon-container.sh /workspace/creator-engine/deploy/daemons/run-daemon-container.sh
   sudoedit /etc/creator-engine/ce-queue-daemon.env
   sudo systemd-analyze verify /etc/systemd/system/ce-queue-daemon.service
   sudo systemctl daemon-reload
   sudo systemctl enable --now ce-queue-daemon.service
   sudo /workspace/creator-engine/deploy/queue-daemon/launch-queue-daemon.sh --health
   ```

3. If systemd cannot be installed on DGX immediately, start the old DGX
   `queue-daemon --loop` launcher from the approved operator account, then
   schedule a follow-up to place DGX under this systemd unit before leaving the
   rollback state.

4. Confirm exactly one daemon is active:

   ```bash
   pgrep -af 'queue-daemon.*--loop'
   ```

   There must be one process total across VPS and DGX.
