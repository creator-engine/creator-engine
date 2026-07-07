---
slug: ce-495-forge-housekeeping-runbook
date: 2026-07-07
kind: story
scope: takeover forge housekeeping operations
issue: ce-ops#495
---

**Codify forge housekeeping runbook.**

- Added the forge housekeeping runbook for standby/takeover controller harvest, review, gate, re-push, closeout, and board hygiene loops.
- Added review-fix coverage for seat-pool intake, pointer-plus-SHA dispatch, empty-conveyor alarms, parallel reviewer fan-out, non-delegable signing, and awaiting-operator communication carve-outs.
- Wired the takeover hydration plan to surface the runbook as an explicit artifact pointer.
- Added the required internal-doc exception ratchet entry and focused takeover hydration test coverage.
- Declared work class: S.
