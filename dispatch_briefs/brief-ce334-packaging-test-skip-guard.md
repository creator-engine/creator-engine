# WORK CLAIM — ce-ops#334 schema-packaging integration test silently SKIPs in CI

**Seat:** dev-1. **Role:** implementer-foreman. **Born foreman** — fan out.

## Branch
```
git fetch origin && git checkout -b ce-334-packaging-test-skip-guard origin/main
```

## Why (self-contained)
The schema-packaging integration test (`validators/tests/integration/test_schema_packaging_wheel.py`) carries `pytest.skip()` guards for the offline lane (no build backend). In CI it **silently SKIPs** — so the build+install+schema-presence check reads as "covered" when it actually never ran (this is the gap that originally hid the #331 schemas-not-packaged bug). The `build` + `setuptools` wheels are now vendored in `validators/wheelhouse-dev/` on main, so the test SHOULD be able to run.

## Task
1. Add an **assert-not-skipped guard** so the test FAILS LOUDLY if it skips in the lane where it must run (don't let a skip read as a pass).
2. Confirm the CI offline lane actually picks up the vendored `validators/wheelhouse-dev/` `build`/`setuptools` wheels so the test RUNS end-to-end (build → install → assert schemas present). If the lane can't, wire it so it can, or make the skip explicit + asserted (documented, not silent).

## Allowed paths (nothing else)
`validators/tests/integration/test_schema_packaging_wheel.py`, `.github/workflows/validate.yml`, `validators/wheelhouse-dev/` (only if a missing dep must be vendored), `.ce/changelog/**`, `.ce/pr-manifests/**`.

## Evidence (DoD)
Full `ce validate-pr` GREEN, and demonstrate the packaging test now RUNS (not skips) in the target lane.
⚠️ **G5 BODY FORMAT (mandatory):** PR body MUST contain exactly ONE line precisely `- **Declared work class:** <tiny|story|feature|epic>` (a `**Work class:**` header / `[PASS]` log line does NOT match — this papercut failed 4 PRs tonight).

## Stop-line
- Green + self-push works → push + PR ref ce-ops#334. Do NOT approve/merge/enqueue.
- Preflight RED → STOP + report the failing gate.
