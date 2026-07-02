---
slug: ce-n2-triage-pickup-filter
date: 2026-07-02
kind: added
scope: advisory ce-ops triage pickup filter
---

Adds an advisory ready-to-dispatch pickup filter to the ce-ops triage queue.

- New pure pickup-candidate projection reuses the existing triage queue
  classifier/readiness path and `forge_triage.readiness_blockers` instead of
  forking readiness logic.
- Existing triage queue scan JSON now includes a `pickup` payload containing
  issue numbers, labels, work class, mutation class, lane, and readiness for
  ready, unblocked, unassigned candidates only.
- Unit coverage verifies ready inclusion, blocked/assigned/in-progress
  exclusion, deterministic ordering, dry-run/no-mutation behavior, and empty
  output.

The filter is advisory only and does not authorize dispatch or perform any new
forge mutations.
