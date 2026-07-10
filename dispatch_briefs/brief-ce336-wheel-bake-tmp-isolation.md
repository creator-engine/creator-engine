# WORK CLAIM — ce-ops#336 wheel-bake test not robust to a stale `validators/build/` dir

**Seat:** dev-3 (VPS contained). **Role:** implementer-foreman. **Born foreman** — fan out.

## Branch
```
git fetch origin && git checkout -b ce-336-wheel-bake-tmp-isolation origin/main
```

## Why (self-contained)
The wheel-bake gate test builds via `build_app_wheel_from_source(repo_root, …)` using the REAL `repo_root`. A leftover `validators/build/` directory from a prior/parallel preflight run poisons the build → **false-RED in local `ce validate-pr`** even when the change under test is clean (the same test passes on clean origin/main and once the stray `build/` is removed). `wheel_bake.py` cleans `build/` at start/end of `_build_wheel`, but the test still uses the live tree.

## Task
Make the wheel-bake test build into an ISOLATED tmp build root (or robustly clean `build/` first) so a leftover `validators/build/` in the working tree cannot poison it. Prefer passing an explicit tmp build dir into `build_app_wheel_from_source` in the test.

## Allowed paths (nothing else)
`validators/creator_engine_validator/wheel_bake.py` (only if a param is needed), `validators/tests/unit/test_wheel_bake.py`, `.ce/changelog/**`, `.ce/pr-manifests/**`.

## Evidence (DoD)
Full `ce validate-pr` GREEN.
⚠️ **G5 BODY FORMAT (mandatory):** PR body MUST contain exactly ONE line precisely `- **Declared work class:** <tiny|story|feature|epic>` (a `**Work class:**` header / `[PASS]` log line does NOT match). Likely `tiny`.

## Stop-line
- Green + push works → push + PR ref ce-ops#336. Do NOT approve/merge.
- Green but push FAILS (self-push gap #337) → STOP + report `READY-FOR-HARVEST: branch ce-336-wheel-bake-tmp-isolation, <N> commits, preflight GREEN`.
- Preflight RED on a NEW gate → STOP + report it.
