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
- Consolidated the duplicate "Stuck Lease Recovery" section in
  `deploy/conveyor-daemon/RUNBOOK.md` down to a short symptom + pointer at
  this canonical runbook, and migrated the live-lease refusal message (a
  fact that existed only in the older doc) into the Symptom section here.
