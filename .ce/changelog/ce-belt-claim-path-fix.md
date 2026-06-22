---
slug: ce-belt-claim-path-fix
ticket: ce-ops#55
type: fix
scope: pickup belt claim path
---

Fixes the pickup belt claim path after the Search-backed canary reached S2 and
crashed before writing claim evidence.

- Replaces stale `_versions.V3_LOCAL_STATE_ROOT` references in `ce pickup poll
  --claim` paths with the already imported `V3_LOCAL_STATE_ROOT`.
- Adds an offline regression for `pickup poll --claim` with launch disabled:
  fake Search returns one work item, the claim is recorded in the default pickup
  ledger, and no lane is spawned without `--enable-launch`.
