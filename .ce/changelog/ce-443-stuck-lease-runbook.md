---
slug: ce-443-stuck-lease-runbook
date: 2026-07-05
kind: added
scope: playbooks/controller/runbooks
issue: ce-ops#443
---

**Add conveyor daemon stuck-lease recovery runbook.**

- Added an operator runbook for `DaemonLeaseStale` after an exit-74 heartbeat
  crash, including the fail-closed rationale, `pgrep` live-process checks,
  stale lease removal, launcher relaunch, and the armed semantics of
  `--one-shot`.
