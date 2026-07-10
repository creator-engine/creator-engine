# DISPATCH BRIEF — dev-4 — ADR-0005 implementation slice 1: mediated brain-append daemon skeleton
Dispatched: 2026-07-06 ~04:5xZ by CE-DEV-2 (controller). Role: implementer, contained seat, COMMIT-ONLY → controller harvests. Authority: day-arc 2026-07-06 R4 (slice-1 dispatch pre-authorized on ratification; ADR-0005 RATIFIED, merged PR #848).

## Unit
- Source of truth: docs/adr/ADR-0005-mediated-brain-ledger-append.md §7 "Minimal Phase-1 slice" (pull fresh origin/main FIRST — the Ratified version with amendments is what you implement against).
- Branch: `ce-adr0005-s1-append-daemon` off FRESH origin/main.
- Worktree: /var/tmp/ce-adr0005-s1-append-daemon (your standard layout; no venv activate).
- Declared work class: **story** (CI enum tiny|story|feature|epic). Keep the unit BOUNDED (~≤400 net lines); if the honest implementation exceeds that, STOP at a coherent skeleton boundary and report the split you propose.

## Scope (mandate D-C: skeleton + mediation-evidence EMISSION; the merge-gate evidence REQUIREMENT is a LATER slice — do not touch merge-gate/CI policy)
1. Data-only append-intent ENVELOPE (schema + loader/validator) for exactly two intent kinds: one active-assertion append, one ce-411-style supersede pair. No ledger record schema changes.
2. Host-side brain-append worker skeleton: consumes ONE intent at a time from a durable file-queue directory, materializes current origin/main ledger, assigns sequence + prev_hash, recomputes hashes, runs the EXISTING brain_runtime ledger validation (reuse, do not fork it).
3. Exactly two outcome paths: (a) committed carrier branch/patch + mediation-evidence artifact; (b) fail-closed refusal naming the violated invariant. No third state.
4. The contained-seat boundary per ADR §7: seat never chooses host paths, final chain position, or final ledger bytes — encode this in the envelope design (intent carries content, not positions).
5. Tests: unit tests for envelope validation (reject malformed/position-bearing intents), sequencing/prev_hash assignment, both outcome paths incl. at least one named-invariant refusal.

## Allowed paths (territory-checked; collision → STOP+report)
- NEW validators/creator_engine_validator/brain_append_* (module(s) + envelope schema file)
- validators/tests/ (new test file(s))
- .ce/changelog/ce-adr0005-s1-append-daemon.md + carrier
DO NOT touch: .ce/brain/assertions.yaml (NO live ledger mutation in this slice), brain_runtime validation internals (reuse only), merge-gate/queue-daemon code, .github/workflows/*, public_docs_confidentiality.py (dev-1 in-flight), dependency_unlock.py, onboard_apply.py, list-checks/digest code (dev-3 in-flight).

## Evidence bar + stop lines
- FULL `ce validate-pr` (CI-parity) GREEN one pass, then COMMIT-ONLY (clean tree at your READY sha) — you do NOT push; controller harvests. Signal: final line `READY <sha>` in your report.
- Carrier via carrier_gen `write_carriers(base="origin/main")`; stem == branch slug; changelog fragment required.
- STOP lines: sha256-pinned/signed-chain file needed → STOP+report (release op). Signature invalid → STOP, report bytes; controller signs. Any path outside allowed set → STOP+report. No approvals/merges/issue writes.
