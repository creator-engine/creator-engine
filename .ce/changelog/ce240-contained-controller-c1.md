---
slug: ce240-contained-controller-c1
date: 2026-06-25
kind: feature
scope: deploy/dgx-controller-runsc
issue: ce-ops#240
---

**Contained controller runsc C1 scaffold.**

- Reworked the DGX contained-controller runsc scaffold to remove ambient Claude token pass-through and use a documented transport-deputy credential-injection seam stub only.
- Added the controller design note covering architecture, credential injection, C3 parity, and C4 cutover.
- Added dry-run shell and unit coverage for contained defaults, forbidden host control sockets, detached launch behavior, and no token leakage.
