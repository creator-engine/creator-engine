---
slug: ce246-integrator-latest-rollup
date: 2026-06-25
kind: fix
scope: ce-ops
issue: ce-ops#246
---

**Integrator daemon uses latest required rollup checks.**

Fixes daemon rollup gating so duplicate required check names are evaluated by
their latest run timestamp, with deterministic observed-order fallback when
timestamps are absent or equal. This prevents stale failed runs from blocking a
green, approved PR while preserving fail-closed behavior for missing or latest
non-success required checks.
