---
slug: ce-fix-artifacts-hint
date: 2026-06-30
kind: fix
scope: validators
issue: ce-fix-artifacts-hint
---

**Fix completion-report artifacts inspect hints.**

- Fixed completion-report evidence-chain and spend inspect hints to call
  `ce artifacts <scope_id> --run-id <run_id>` instead of passing the run id as
  the required scope positional.
- Added regression coverage for the v3 report artifact enumeration inspect
  command shape.
