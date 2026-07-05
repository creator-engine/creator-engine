# Conveyor Daemon Stuck-Lease Recovery Runbook

> **Canonical location.** This is the canonical conveyor-daemon stuck-lease
> recovery procedure. `deploy/conveyor-daemon/RUNBOOK.md` points here instead
> of duplicating the steps; keep this file authoritative for any lease-recovery
> change.

Use this runbook when the conveyor daemon refuses to restart after a heartbeat
crash and reports `DaemonLeaseStale`.

This is an operator recovery path for a fail-closed singleton lease. It must not
be used to take over a live daemon.

## Symptom

After an exit-74 crash, a restart exits with status `73` and logs a stale lease
refusal similar to:

```text
ERROR: conveyor-daemon singleton lease refused: stale conveyor-daemon lease requires explicit audited takeover; lease_path=/path/to/conveyor-daemon.lease; holder_pid=12345
```

A restart can also refuse because another holder is genuinely live, not stale:

```text
ERROR: conveyor-daemon singleton lease refused: live conveyor-daemon lease is held by conveyor-daemon:otherhost:12345 pid=12345 host=otherhost; lease_path=/path/to/conveyor-daemon.lease; holder_pid=12345
```

A stale-lease refusal means the recorded holder pid is dead (safe to recover
below). A live-lease refusal means another holder and pid are named directly in
the message; do not remove the lease or treat it as stale — investigate or stop
that live daemon cleanly instead.

The expected lease file is the daemon lease root plus the daemon name:
`${CE_DAEMON_LEASE_ROOT}/conveyor-daemon.lease`. The reusable lease helper also
defaults its state root to `.ce/state/daemon-leases`; production launchers set
`CE_DAEMON_LEASE_ROOT` explicitly.

## Why This Fails Closed

The conveyor daemon is armed: it can open pull requests and mutate repository
state. Startup therefore uses a singleton lease with stale takeover disabled.

The launcher also runs a heartbeat thread. If heartbeat writing fails, that
thread terminates the process with `os._exit(74)`. That bypasses Python cleanup,
including the normal `lease.release()` path, so the lease file can remain on
disk after the holder process is gone. The next launch sees a stale lease and
raises `DaemonLeaseStale` instead of silently replacing it.

This is intentional. Automatic takeover could permit two daemon instances to run
after clock skew, filesystem delay, or an unobserved live holder.

## Recover

1. Resolve the active lease path from the launcher environment.

   ```bash
   grep -E '^CE_DAEMON_LEASE_ROOT=' /etc/creator-engine/ce-conveyor-daemon.env
   set -a
   . /etc/creator-engine/ce-conveyor-daemon.env
   set +a
   lease_path="${CE_DAEMON_LEASE_ROOT:?}/conveyor-daemon.lease"
   sudo test -f "$lease_path"
   sudo cat "$lease_path"
   ```

2. Verify that no conveyor daemon process is live before removing anything.

   ```bash
   pgrep -af 'creator_engine_validator.conveyor_daemon_runner|deploy/conveyor-daemon/launch-conveyor-daemon.sh|run-daemon-container.sh conveyor-daemon'
   ```

   If this prints a process, stop. Investigate or stop the live daemon cleanly
   instead of removing the lease.

3. Verify the lease holder pid specifically with `pgrep`.

   ```bash
   holder_pid="$(sudo python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["pid"])' "$lease_path")"
   tmp_pidfile="$(mktemp)"
   printf '%s\n' "$holder_pid" > "$tmp_pidfile"
   pgrep -a -F "$tmp_pidfile"
   rc=$?
   rm -f "$tmp_pidfile"
   test "$rc" -eq 1
   ```

   `pgrep -F` returning `1` is the pass condition: the recorded holder pid is
   absent. Any printed process means the holder is live; do not remove the
   lease.

4. Remove the stale lease file only after both live-process checks pass.

   ```bash
   sudo rm -- "$lease_path"
   ```

5. Relaunch through the canonical launcher path.

   For the managed service:

   ```bash
   sudo systemctl restart ce-conveyor-daemon.service
   sudo systemctl status ce-conveyor-daemon.service
   ```

   For a foreground operator run from the repository root, use the launcher
   directly with the same environment file:

   ```bash
   set -a
   . /etc/creator-engine/ce-conveyor-daemon.env
   set +a
   /workspace/creator-engine/deploy/conveyor-daemon/launch-conveyor-daemon.sh
   ```

## One-Shot Is Armed

`deploy/conveyor-daemon/launch-conveyor-daemon.sh --one-shot` runs exactly one
daemon pass, but it is still an armed pass. It has the same real side effects as
the loop for that pass; it is not a rehearsal, dry run, or disarmed mode.
