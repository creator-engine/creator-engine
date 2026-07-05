---
slug: ce-411-brain-drift-tombstone-invariants
date: 2026-07-05
kind: story
scope: validators/creator_engine_validator/checks/ce_brain_drift.py duplicate-ID tombstone invariants + unit tests + changelog
issue: creator-engine/ce-ops#411
---

**Brain drift tombstone invariants.**

- Hardened `ce brain verify --drift` with duplicate assertion ID tombstone invariants.
- Added drift-local error codes for duplicate active IDs, dangling `superseded_by`, and tombstone-ordering violations.
- Covered invalid duplicate/tombstone shapes and a valid chained-supersede fixture in unit tests.
