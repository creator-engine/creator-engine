---
slug: ce-474-verify-reference-mode
date: 2026-07-06
kind: fixed
scope: onboard apply / brownfield verification
issue: ce-ops#474
---

**Honor declared reference protections during preserved-check verify.**

- Honor an explicit `github.protections: reference` declaration when preserved-check verification hits a GitHub plan/capability 403.
- Keep undeclared 403 responses fail-closed as `protection_floor_unenforceable`.
- Record `protection_floor: documented-not-enforced` evidence with repo, branch, and declared mode.
