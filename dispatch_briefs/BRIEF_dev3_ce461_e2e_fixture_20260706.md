# DISPATCH BRIEF — dev-3 — ce-ops#461: e2e fixture for validate-pr merge-group parity (respawned #428c)
Dispatched: 2026-07-06 ~07:1xZ by CE-DEV-2 (controller). Role: implementer, contained seat, COMMIT-ONLY → controller harvests. Day-arc lane D-B restock.

## Unit
- Ticket: creator-engine/ce-ops#461 — parent #428 part (c): parts (a)+(b) landed via #830/#834 (workflow template + client-repo profile). This unit verifies that product fix end-to-end with a REAL non-CE-shaped client repo fixture through the full adoption+CI lifecycle (merge-group parity test).
- Branch: `ce-461-adoption-e2e-fixture` off FRESH origin/main (fetch first — main is at the #853+ era; your cached origin/main is stale).
- Worktree: /var/tmp/ce-461-adoption-e2e-fixture. Declared work class: **story** (enum tiny|story|feature|epic; ticket wc:S).

## Scope
1. Build a minimal NON-CE-shaped fixture repo (in-tree fixture dir, e.g. validators/tests/fixtures/<name>/ — follow the existing fixture conventions you find; it must look like a plausible client project: own README/src/tests/CI, NO .ce/, no CE markers).
2. Integration test driving the adoption path (#830's workflow template + #834's client-repo profile) against that fixture: adoption produces the expected scaffold/workflow, and validate-pr runs with MERGE-GROUP PARITY (the checks the merge group would run == the checks the PR run declares) on the adopted fixture.
3. Failure-direction coverage: the parity assertion must actually fail if the template and profile drift apart (e.g. a check present in one set and not the other) — prove by test construction, not just happy path.
4. Read #830/#834's merged diffs first (git log/show on origin/main) so the test exercises THEIR seams, not a parallel reimplementation.

## Allowed paths (territory-checked; collision → STOP+report)
- validators/tests/ (new integration test + fixture directory)
- .ce/changelog/ce-461-adoption-e2e-fixture.md + carrier
DO NOT touch: product code under validators/creator_engine_validator/ (this is a TEST unit — if the e2e reveals a product bug, STOP and report it as a finding instead of fixing inline), .github/workflows/*, release staging/downloads (release in progress), brain_append_* (in-flight).

## Evidence bar + stop lines
- FULL `ce validate-pr` (CI-parity) GREEN one pass, then COMMIT-ONLY (clean tree). Signal: final line `READY <sha>`.
- Carrier via carrier_gen `write_carriers(base="origin/main")`; stem == branch slug; changelog fragment required.
- STOP lines: sha256-pinned/signed-chain file → STOP+report. Signature invalid → STOP; controller signs. Product-code change needed → STOP+report finding. No pushes/approvals/merges/issue writes.
