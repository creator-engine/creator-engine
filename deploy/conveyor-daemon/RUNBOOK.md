# Conveyor Daemon Runbook

## Stuck Lease Recovery

The service repeatedly exits with status `73` and a stale- or live-lease
refusal (`DaemonLeaseStale`) when
`${CE_DAEMON_LEASE_ROOT}/conveyor-daemon.lease` already exists and cannot be
safely replaced.

For the symptom, verification, and recovery steps, see the canonical runbook:
`playbooks/controller/runbooks/conveyor-daemon-stuck-lease.md`.
