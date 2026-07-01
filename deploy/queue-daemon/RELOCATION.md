# Queue Daemon Relocation Runbook

This package moves the merge-queue daemon from an ad-hoc DGX launch into a
boot-persistent systemd service. The same persistence applies whichever host
runs the unit: CE-DEV-1 VPS for cutover, or DGX again during rollback.

## Files

- `ce-queue-daemon.service`: system service with `Restart=always`,
  `RestartSec=5`, journald logging, start-limit protection, and
  `WantedBy=multi-user.target`.
- `launch-queue-daemon.sh`: fail-closed launcher for `v3_cli queue-daemon` with
  a `--health` mode.
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
   sudo install -m 0644 deploy/queue-daemon/ce-queue-daemon.service /etc/systemd/system/ce-queue-daemon.service
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
   ```

   The unit pins `BAO_ADDR=https://100.72.252.20:8200`, and sets runtime/state
   paths under `/run/ce-queue-daemon` and `/var/lib/ce-queue-daemon`.

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
   `Restart=always` and boot persistence apply on DGX too.

   ```bash
   sudo install -d -m 0755 /etc/creator-engine
   sudo install -m 0644 deploy/queue-daemon/ce-queue-daemon.service /etc/systemd/system/ce-queue-daemon.service
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
