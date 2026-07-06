---
slug: ce-467-version-drift-gate
date: 2026-07-06
kind: feat
scope: validate-pr / CI version surfaces
issue: ce-ops#467
---

**Add current-version drift gate.**

- Added an explicit version-drift gate and direct CLI path for unsigned current-version docs and deploy surfaces.
- Wired the gate into local `ce validate-pr` and the validate workflow without changing workflow permissions.
- Updated stale unsigned deploy image defaults to the current `0.3.3` release and added stale/current/historical regressions.
