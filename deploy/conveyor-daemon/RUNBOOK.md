# Conveyor Daemon Runbook

## Stuck Lease Recovery

The conveyor daemon is a singleton. It refuses to start when
`${CE_DAEMON_LEASE_ROOT}/conveyor-daemon.lease` already exists and the lease
cannot be safely replaced.

### Symptom

The service repeatedly exits with status `73`, and `journalctl` shows a lease
refusal such as:

```text
ERROR: conveyor-daemon singleton lease refused: stale conveyor-daemon lease requires explicit audited takeover; lease_path=/path/to/conveyor-daemon.lease; holder_pid=12345
```

A live lease may report that the lease is held by another holder and pid. A
stale lease reports that explicit audited takeover is required.

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
