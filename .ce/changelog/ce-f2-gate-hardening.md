---
slug: ce-f2-gate-hardening
date: 2026-07-10
kind: fix
scope: gate
issue: VPS_STORAGE_GATE_INCIDENT_20260710
---

**Gate hardening: homeless attempt log, disk-headroom refusal, liveness state export.**

Implements F-2 from `VPS_STORAGE_GATE_INCIDENT_DESIGN_20260710.md §C/F-2`, three
behaviors that prevent the merge-gate crashloop that occurred when the root disk
hit 0 bytes (05:24–05:30 UTC 2026-07-10):

- **F-2.1 — Homeless attempt log (`deploy/daemons/run-daemon-container.sh`):**
  `setup_attempt_log` no longer depends on `$HOME` for the log directory. Fallback
  order is now: `CE_DAEMON_LOG_DIR` → `LOGS_DIRECTORY` (systemd `LogsDirectory=`
  injection) → journald-only degradation (warning to stderr, daemon continues).
  Every failure path emits a `WARNING:` to stderr and returns successfully; the
  daemon NEVER exits because a log file cannot be created.

- **F-2.1b — `LogsDirectory=` unit addition (`deploy/queue-daemon/ce-queue-daemon.service`):**
  Added `LogsDirectory=ce-queue-daemon` / `LogsDirectoryMode=0700` so systemd
  provisions `/var/log/ce-queue-daemon` and exports it as `LOGS_DIRECTORY` for
  the contained launch path.

- **F-2.2 — Startup disk-headroom check (`deploy/queue-daemon/launch-queue-daemon.sh`):**
  Added `check_disk_headroom` function that runs in `main_uncontained` after
  `validate_required_env` but BEFORE `exec_with_queue_daemon_lease`. If the
  filesystem hosting `CE_DAEMON_STATE_ROOT` (or nearest existing ancestor) has
  fewer than `CE_DAEMON_DISK_HEADROOM_GB` GiB free (default 5), the script exits
  with code **75** and an error message naming `disk_headroom`. This refusal
  happens before the singleton lease is acquired so a low-disk boot does not
  block future lease takeover.

- **F-2.3 — Liveness state export (`validators/creator_engine_validator/forge/integrator_belt.py`):**
  `run_daemon_loop` accepts a new `liveness_state_path` keyword argument (falls
  back to `CE_DAEMON_LIVENESS_STATE_PATH` env var). After each `daemon_pass_complete`
  log entry, `_write_liveness_state` atomically refreshes a JSON file containing
  `last_pass_timestamp`, `pass_index`, and `failed_count`. Write failures are
  non-fatal (warning to stderr, loop continues). An external watchdog can now
  detect stale passes without parsing docker logs.

Extend-don't-weaken: all existing tests pass without modification.
