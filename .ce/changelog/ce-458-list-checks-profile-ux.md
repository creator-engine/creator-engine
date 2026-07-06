---
slug: ce-458-list-checks-profile-ux
date: 2026-07-06
kind: fixed
scope: validator CLI list-checks profile UX
issue: ce-ops#458
---

**Profile-aware list-checks output.**

- `--list-checks --profile client-repo` now lists only the effective check set after applying the profile omissions.
- Unprofiled `--list-checks` remains byte-identical to the full registered check inventory.
- Added focused CLI tests for profiled filtering and unprofiled output stability.
