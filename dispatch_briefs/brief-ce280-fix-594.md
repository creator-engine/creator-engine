# WORK CLAIM — fix PR #594 (ce-ops#280) per independent review (REQUEST_CHANGES)

**Seat:** dev-1 (you authored #594). **Role:** implementer-foreman. **Born foreman** — fan out.

## Branch
Your existing `ce280-ci-build-args-from-surfaces` (the #594 branch). `git fetch origin && git rebase origin/main` first.

## Context
PR #594 got REQUEST_CHANGES on independent review. The render.py build-arg **wiring is correct/additive (no regression) — good.** But two BLOCKING merge-order dependencies make it un-mergeable standalone (they fail in the **merge queue**, not the PR-level governance check):

### Blocker 1 — brain-assertion ordering
#594 adds a brain assertion (seq 10 in `.ce/brain/assertions.yaml`) anchored to seq 9, but origin/main has only seq 0–6 (seq 7/8/9 live only in OTHER in-flight branches: `wt-ce-release-030`, `wt-ce292-harvest`). So `test_ce_brain_drift`'s `assert len(active)==10` FAILS in the merge queue.
**Fix (pick one, prefer DECOUPLE):**
- **Decouple** — drop the brain-assertion addition from this PR entirely. A CI-build-args change should not depend on the brain ledger. (Preferred.)
- Or re-anchor the assertion to current-main HEAD sequence, re-cast the test to be baseline-safe (`assert len(active) >= N`, not `==10`), AND declare the ordering in the PR manifest.

### Blocker 2 — manifest-entry dependency
`test_oci_build_script…` / `test_non_oci_build_wrappers…` assert `OCI_CPYTHON_BASE_IMAGE_*` / `RUST_*` / `DEBIAN_*` build-args render, but those surface entries don't exist in `surfaces/manifest.yaml` on main.
**Fix:** add the required Docker-image surface entries to `surfaces/manifest.yaml` in THIS PR (so the tests have data), OR make the tests skip-if-absent and declare the prereq in the PR manifest.

### Non-blocking
`_env_key` is duplicated between `surfaces/render.py` and `validators/creator_engine_validator/checks/surfaces_manifest.py` — prefer `from surfaces.render import _env_key` to avoid drift.

## Goal / DoD
#594 mergeable STANDALONE against current origin/main. Run the FULL `ce validate-pr` (CI-parity, full suite incl. brain-drift + build-wiring tests) GREEN on a clean rebase. Push to update #594.

## Stop-line
- Green + pushed → report `#594 UPDATED, preflight GREEN`. Do NOT merge (controller gates).
- Preflight RED → STOP + report the failing gate.
