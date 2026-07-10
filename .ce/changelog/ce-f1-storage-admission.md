---
slug: ce-f1-storage-admission
date: 2026-07-10
kind: feat
scope: disk headroom admission + scratch reaper slice 1
issue: VPS_STORAGE_GATE_INCIDENT_DESIGN_20260710 §C/F-1.2+F-1.3
---

**Suite disk-headroom admission gate + deterministic scratch reaper (F-1.2 + F-1.3 slice 1).**

Addresses the recurrent 100%-disk fill class identified in the 2026-07-10 VPS storage-gate incident.

**F-1.2 — Headroom admission gate:**
- New module `validators/creator_engine_validator/disk_headroom.py` exposing `check_headroom(path, min_free_gb)`, `free_gb(path)`, `DiskHeadroomError`, and `effective_min_free_gb()`.
- `pr_preflight.py` gains a `disk_headroom (suite pre-flight)` check that runs immediately before the baseline-diff test command stage.  The gate fails-closed (returns 1) with a message naming `disk_headroom` and the measured free GiB when space is below the threshold (default 30 GiB; overridable via `CE_SUITE_MIN_FREE_GB`).  The pytest suite is never spawned when this check fails.

**F-1.3 slice 1 — Deterministic scratch reaper:**
- New script `deploy/storage-reaper/reap-scratch.sh`: sweeps `/var/tmp/wt-*` (48h), `/var/tmp/pt-*` (24h), and dangling Docker images.  Logs reclaimed bytes per category to stdout (journald when run under systemd).  Idempotent, refuses nothing, shellcheck-clean.  Supports `--dry-run` flag.
- Systemd service template `ce-storage-reaper.service` + daily timer `ce-storage-reaper.timer` (Persistent=true, 30-minute RandomizedDelaySec).

**Tests:**
- 18 unit tests for `disk_headroom.py` (threshold pass/fail via `os.statvfs` mock, env override, `DiskHeadroomError` attributes) plus preflight integration tests confirming the gate blocks before pytest and passes with adequate disk.
- 8 subprocess tests for `reap-scratch.sh --dry-run` including aged-fixture detection (wt-* at 50h, pt-* at 30h), below-threshold exclusion, no-delete guarantee, and unknown-flag exit.
