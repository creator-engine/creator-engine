---
slug: ceops95-seat-lifecycle-phase1
date: 2026-06-16
kind: added
scope: substrate / governed seat lifecycle registration
issue: creator-engine/ce-ops#95
base: 3e6b516dd35e6a4350696a70dc90cb48369cfc97
---

Phase 1 of ce-ops#95 adds deterministic spawn-time seat lifecycle
registration for `ce launch` and `ce lane launch`.

- Added `schemas/seat-lifecycle.schema.yaml` and a shared
  `seat_lifecycle` runtime with atomic YAML record writes, append-only NDJSON
  audit events, registration-failure escalation, default governed-seat policy
  constants, and injectable tmux/proc/git probe seams for later sampling.
- `ce launch` and `ce lane launch` now register one lifecycle object after the
  pane spawn/resource-confirm point. Dry-runs remain pure. Registration failure
  emits a loud warning plus an `AWAITING-OPERATOR` escalation and proceeds
  ungoverned for this compatibility release behind
  `SEAT_LIFECYCLE_FAIL_CLOSED = False`.
- Added lifecycle refs to launch results and CLI JSON, and persisted
  `--claim-ticket` work-claim bindings into the lifecycle record.
- Rebuilt the validator app wheel and refreshed `validators/wheelhouse/SHA256SUMS`.

Not included: `ce seats ls`, sampling/read-model surfaces, cockpit integration,
policy reaper integration, and backlog reaping. Those remain later phases.
