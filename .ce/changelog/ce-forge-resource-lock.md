---
slug: ce-forge-resource-lock
date: 2026-06-28
kind: added
scope: validator forge tooling
issue: ce-ops#34
---

**Add local forge resource locks.**

- **Declared work class:** story
- Added self-contained forge resource locks backed by local `.ce/state` JSON records.
- Covered acquire/release/status/listing, contention refusal, stale reclaim, and holder release ownership.
