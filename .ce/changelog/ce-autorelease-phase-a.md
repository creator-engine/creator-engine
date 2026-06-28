---
slug: ce-autorelease-phase-a
date: 2026-06-28
kind: added
scope: validator CLI - autonomous release changelog
issue: ce-ops#315
---

Complete the `release-changelog` seam with deterministic dated notes and a
separate GitHub release body, while preserving all source fragments in place.

- Accept both current (`kind`/`issue`) and legacy (`type`/`ticket`) changelog
  front matter.
- Expose a runtime-free towncrier-compatible adapter/config instead of adding a
  network dependency or pretending the towncrier runtime is available.
- Add CLI `--date` and `--github-out` support alongside `--out` and `--json`.
