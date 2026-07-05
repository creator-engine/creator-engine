# Conveyor Daemon Runbook

## Stuck Lease Recovery

The conveyor daemon is a singleton. It refuses to start when
`${CE_DAEMON_LEASE_ROOT}/conveyor-daemon.lease` already exists and the lease
cannot be safely replaced.

### Symptom

The service repeatedly exits with status `73`, and `journalctl` shows a lease
refusal such as:

Stale lease (heartbeat-crash survivor — requires manual cleanup):

```text
ERROR: conveyor-daemon singleton lease refused: stale conveyor-daemon lease requires explicit audited takeover; lease_path=/path/to/conveyor-daemon.lease; holder_pid=12345
```

Live lease (another instance is genuinely running):

```text
ERROR: conveyor-daemon singleton lease refused: live conveyor-daemon lease is held by conveyor-daemon:otherhost:12345 pid=12345 host=otherhost; lease_path=/path/to/conveyor-daemon.lease; holder_pid=12345
```

A stale lease reports that explicit audited takeover is required. A live lease
reports that the lease is held by another holder and pid.

### Verify

Identify the configured lease root and inspect the lease:

```bash
systemctl cat ce-conveyor-daemon.service
grep -E '^CE_DAEMON_LEASE_ROOT=' /etc/creator-engine/ce-conveyor-daemon.env
lease_path="${CE_DAEMON_LEASE_ROOT:?}/conveyor-daemon.lease"
sudo cat "$lease_path"
```

Confirm the recorded pid is no longer alive before removing anything:

```bash
holder_pid="$(sudo python3 - "$lease_path" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text())
print(payload["pid"])
PY
)"
ps -p "$holder_pid" -o pid=,comm=,args=
```

If `ps` prints a process, do not remove the lease. Investigate the running
daemon or stop it cleanly.

### Recover

When the holder pid is dead, remove the lease file and restart the service:

```bash
lease_path="${CE_DAEMON_LEASE_ROOT:?}/conveyor-daemon.lease"
sudo rm -- "$lease_path"
sudo systemctl restart ce-conveyor-daemon.service
sudo systemctl status ce-conveyor-daemon.service
```

### Why Takeover Is Manual

The daemon opens pull requests and mutates repository state. Automatic stale
lease takeover could allow two daemon instances to run concurrently after clock
skew, filesystem delay, or an unobserved crash. The daemon therefore fails
closed: an operator must verify that the recorded holder process is dead before
removing the lease and restarting.

Stale leases are a real, expected outcome of the launcher's own crash-safety
design, not just a theoretical edge case. The launcher runs a background
heartbeat thread alongside the daemon's main loop. If a heartbeat write fails,
that thread exits the whole process immediately via `os._exit(74)` rather than
returning normally. `os._exit` skips Python's normal cleanup path, so the main
loop's `finally: lease.release()` never runs and the lease file is left on
disk exactly as it was before the crash. The next launch attempt then finds a
lease that looks live but whose recorded pid is gone, which is reported as a
stale lease (`DaemonLeaseStale`) and refused fail-closed rather than silently
replaced.
