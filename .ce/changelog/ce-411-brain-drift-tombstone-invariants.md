---
slug: ce-411-brain-drift-tombstone-invariants
date: 2026-07-05
kind: story
scope: validators/creator_engine_validator/checks/ce_brain_drift.py duplicate-ID tombstone invariants + unit tests + brain-ledger evidence re-pin (d1b-19-v3) + active-count ratchet + changelog
issue: creator-engine/ce-ops#411
---

**Brain drift tombstone invariants.**

- Hardened `ce brain verify --drift` with duplicate assertion ID tombstone invariants.
- Added drift-local error codes for duplicate active IDs, dangling `superseded_by`, and tombstone-ordering violations.
- Covered invalid duplicate/tombstone shapes and a valid chained-supersede fixture in unit tests.
- Superseded `brain-assertion-d1b-19-brain-drift-state-reconcile-v2` → `-v3` to re-pin `evidence_sha256` to this branch's own edited `ce_brain_drift.py` (the drift check's own hash-pin obligation, verified against the new invariants it adds).
- Bumped the authoritative-ledger active-count ratchet in `test_ce_brain_drift.py` (append-only tombstoning adds one raw active-status row per supersede) and repointed its known-pin exception to the new `-v3` id.
