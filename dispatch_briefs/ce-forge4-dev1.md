# BRIEF — dev-1 — Forge-side epic slice FORGE-4 (ce-ops#34): resource locks

Born-foreman, non-contained (SELF-PUSH as ce-dev-1). Drive to a green PR. Stay in allowed paths.

## Goal
Add a forge-side RESOURCE-LOCK module so concurrent governed work can claim/release a shared resource (a worktree, a PR, a branch territory) without colliding — the programmatic backbone for the territory-map discipline. Read `docs/design/ce-forge-side-automation.md` (ON MAIN) §resource-locks/ops-board and `docs/architecture/work-claim-locks.md` (ON MAIN) for the existing doctrine; build the module to match it.

## PROBE FIRST (verify-not-already-landed)
Grep for an existing resource-lock / work-claim-lock implementation under `validators/creator_engine_validator/`. If a `resource_lock.py` (or equivalent claiming the same responsibility) already exists, STOP and report — do not duplicate. Build only the missing piece.

## Branch
`ce-forge-resource-lock` off current `origin/main`. Fresh worktree.

## Allowed paths (HARD limit)
- `validators/creator_engine_validator/forge/resource_lock.py` (NEW) — a self-contained module: acquire(resource_id, holder, *, ttl)/release/is_held/list_held, backed by a simple on-disk lock record under `.ce/state/` (atomic create, stale-TTL reclaim, holder identity recorded). No network. Fail-closed (refuse on contended lock).
- `validators/tests/unit/test_resource_lock.py` (NEW)
- `.ce/changelog/ce-forge-resource-lock.md`, `.ce/pr-manifests/ce-forge-resource-lock.md`
Do NOT import from or touch ce_cli.py, the broker, cred_injection_proxy, automerge modules, or schemas. Self-contained module + tests only.

## Gate-coupling note
If adding a new module trips a docs/reference/example-sweep gate, regenerate the required artifact AND include it; if the target is outside these paths, STOP and report. `rm -rf validators/*.egg-info validators/build` before validate.

## Evidence
- FULL preflight GREEN: `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-forge-resource-lock`
- Carriers via carrier_gen (dashed slug); manifest+body carry `- **Declared work class:** story`.
- SELF-PUSH as ce-dev-1, open PR (mention ce-ops#34), report PR# + SHA. Do NOT approve/merge.
