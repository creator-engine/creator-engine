---
slug: ce196-triage-queue-hygiene
ticket: ce-ops#196
type: fix
scope: forge triage queue hygiene
---

Tightens `ce pickup triage` queue hygiene after ce-ops#194 / PR #338.

- Skips issues whose linked PR is open, merged, or otherwise closed as done
  before surfacing pickup mutations.
- Fails closed when a closed linked-PR reference cannot be resolved
  unambiguously through the timeline/detail lookup.
- Skips explicit hold markers such as `AWAITING-OPERATOR` and tracking/meta
  labels as non-claimable queue entries.
- Adds offline unit coverage for merged/closed-done PRs, ambiguous PR detail
  lookup, hold markers, and tracking labels while preserving timeline
  pagination coverage.
