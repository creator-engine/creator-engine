---
slug: ce-brain-ingest-refresh
date: 2026-06-28
kind: added
scope: brain ingest refresh
issue: ce-ops#79
---

**feat(brain): add advisory ingest refresh wrapper.**

Add an advisory scheduled refresh wrapper for the company-brain recall store.

- Adds `scripts/brain-ingest-refresh.sh`, a timer-safe wrapper around `ce brain ingest` for `MEMORY.md` and `docs/` with newest-record `as_of` versus source-mtime drift detection.
- Adds `docs/operations/brain-ingest-refresh.md` with behavior, scheduling, drift detection, and advisory/non-gating status.
- Keeps the slice script/docs/carriers only; no CLI, schema, broker, or validator changes.
- **Declared work class:** story
