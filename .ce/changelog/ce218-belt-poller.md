---
slug: ce218-belt-poller
date: 2026-06-24
kind: added
scope: validator engine (forge.integrator_belt) / ce CLI (queue poll)
issue: ce-ops#218
---

**Integrator belt poller (ce-ops#218 stage 1): wire the merged Integrator
primitives behind a bounded, fail-closed merge-queue poll loop.**

- `forge.integrator_belt` adds a Search-API poll loop chaining the ce216
  primitives: eviction detection -> deterministic resolver -> executor race
  guard -> requeue/merge or controller escalation.
- `ce queue poll` CLI entry; `ce queue dry-run --enqueue/--land/--merge` now
  route through the live belt when `GH_TOKEN` is present, UNDER the existing merge gate.
- Fail-closed: missing token, fork PR heads, moved PR heads/base, semantic
  conflicts, unsafe paths, transport errors, executor refusals all refuse before
  any force/preview write. No force-push path. Preview stays mode=dry-run, has_authority=false.
