# ADDENDUM 3 — ce-446-base-resolve-robust — count-ratchet bump authorized (final blocker)

Your third stop was again correct — and this one is a controller brief-composition miss: the
ratified brain evidence-pin doctrine requires every supersession unit to carry the count-ratchet
bump, and Addendum 1 failed to pre-authorize it.

## Authorization (closed-set extension)
`validators/tests/unit/test_ce_brain_drift.py` is ADDED to your allowed paths, for EXACTLY ONE
change: the hardcoded active-record count in
`test_authoritative_migrated_assertions_validate_and_probe` (87 → 88). That assertion IS the
deliberate ratchet: unnoticed ledger growth fails loudly; deliberate supersessions bump it with
rationale. Touch nothing else in that file.

## Finish the unit
1. Bump the ratchet (87 → 88) with, if the file's style has one, a brief comment/rationale
   consistent with existing entries.
2. Changelog: add one line noting the ratchet bump and why (supersession re-pins the
   validate-workflow assertion after the workflow hardening).
3. Carrier regen to include the test file (stem == branch).
4. FULL validate-pr GREEN one pass — main-vintage invocation per Addendum 2
   (`PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli validate-pr`).
5. Self-push and open the PR per the original brief (work-class line + `Closes
   creator-engine/ce-ops#446`). Build on your commit efdd9156.

All other constraints unchanged. This should be the last round-trip on this unit.
