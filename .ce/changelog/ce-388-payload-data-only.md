---
slug: ce-388-payload-data-only
date: 2026-07-02
kind: fixed
scope: validators/conveyor-daemon
issue: ce-ops#388
---

**Wire ADR-0004 payload schema into conveyor daemon discovery.**

- Wired ConveyorDaemonItem.from_mapping() through the ADR-0004 data-only schema before raw discovery field access.
- Legacy command, base, remote, and path-bearing discovery mappings now reject with value-free audit records.
- Schema-rejected discovery items are isolated per item so one bad payload cannot drop the rest of the batch.
- Added daemon and schema regressions for missing, typed, non-mapping, and legacy-control payload failures.
