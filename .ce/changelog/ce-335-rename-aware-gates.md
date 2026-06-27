---
slug: ce-335-rename-aware-gates
date: 2026-06-27
kind: fixed
scope: validator PR gates
issue: ce-ops#335
---

Made the work-sizing floor and path-manifest PR gates explicitly
rename-aware.

- `verify-work-sizing-floor` now derives its PR diff from
  `git diff --numstat --find-renames`, so pure relocations do not inflate the
  minimum work-class floor.
- `verify-path-manifest` now uses explicit rename detection in both
  single-manifest and per-PR carrier modes, with staged/index shims kept in
  sync.
- Added focused regression tests for pure relocations, genuine large changes,
  carrier path generation, and rename plus unlisted-path containment failures.
