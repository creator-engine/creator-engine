# ce-437 slice 3 - containerize daemons

- Added a fail-closed filesystem lease module for armed daemon singleton gates,
  including atomic acquisition, explicit audited stale takeover, idempotent
  release, and heartbeat updates.
- Required an injected daemon lease for armed conveyor daemon startup while
  leaving disarmed/report-only planning leaseless.
- Added shared daemon container packaging and converted the queue daemon systemd
  path to the contained runner, with `CE_DAEMON_UNCONTAINED=1` documented as the
  legacy direct-launch escape hatch.
- Added a `queue-daemon` singleton lease supervisor to the queue launch path so
  contained and uncontained queue loops share the same live-daemon gate.
- Rework: same-host expired leases now honor live PIDs, conveyor passes
  heartbeat between item boundaries and stop fail-closed on heartbeat loss, and
  the queue supervisor terminates its child with exit 74 on heartbeat errors.
