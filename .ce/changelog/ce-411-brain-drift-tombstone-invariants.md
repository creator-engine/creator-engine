---
slug: ce-411-brain-drift-tombstone-invariants
date: 2026-07-05
kind: story
scope: validators/creator_engine_validator/checks/ce_brain_drift.py duplicate-ID tombstone invariants + unit tests + brain-ledger evidence re-pin (d1b-19-v3) + active-count ratchet + changelog
issue: creator-engine/ce-ops#411
---

**Brain drift tombstone invariants.**

- Hardened `ce brain verify --drift` with duplicate assertion ID tombstone invariants.
- Added drift-local error codes for two genuinely additive invariants: duplicate active IDs (`CODE_DUPLICATE_ACTIVE_ID`) and tombstone-ordering violations (`CODE_TOMBSTONE_ORDER`), covering both the tombstone-before-active and duplicate-tombstone shapes.
- Removed the previously added `_supersede_chain_invariant_errors` / `CODE_INVALID_SUPERSEDE_CHAIN` invariant after reviewer verification that its missing-target/cycle/non-active-terminal shapes are already fully covered by `brain_runtime.validate_ledger_doc` → `CODE_SUPERSEDE_TARGET`.
- Covered duplicate-active-id, duplicate-tombstone, tombstone-before-active, and valid chained-supersede shapes in unit tests.
- Superseded `brain-assertion-d1b-19-brain-drift-state-reconcile-v2` → `-v3` to re-pin `evidence_sha256` to this branch's own edited `ce_brain_drift.py`; then superseded `-v3` → `-v4` after the review-requested deletion of invariant 2 changed the file's sha256 again.
- Bumped the authoritative-ledger active-count ratchet in `test_ce_brain_drift.py` to 90 (two supersedes, two new active-status rows appended) and repointed its known-pin exception to `-v4`.
