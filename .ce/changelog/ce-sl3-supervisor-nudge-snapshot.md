---
slug: ce-sl3-supervisor-nudge-snapshot
date: 2026-07-11
kind: added
scope: validator / supervisor read model
---

**SL-3 supervisor nudge snapshot.**

- Added a pure, typed classifier for injected stale-review, seat, duplicate,
  capacity, queue, coverage, and context-checkpoint observations.
- Proposals are deterministic, deduplicated, and fail closed for malformed or
  incoherent snapshots; this slice has no discovery or actuation surface.
