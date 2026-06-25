---
slug: ce235-emergency-stop-alias
date: 2026-06-25
kind: added
scope: gate-hardening — emergency stop alias for merge-queue dequeue
issue: ce-ops#235
---

**emergency stop alias.**

- Added first-class `emergency-stop` command for the existing merge-queue dequeue primitive.
- Kept `queue-dequeue` as a backcompat alias for the same handler and JSON/exit behavior.
- Operator docs call out that draft conversion or review dismissal alone does not evict an in-flight queue entry.
