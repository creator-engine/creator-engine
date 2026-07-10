# BRIEF — dev-1 — CEO-mode slice CEO-B (ce-ops#313 / forge autonomy)

You are a born-foreman builder seat (non-contained; you SELF-PUSH your own PR as ce-dev-1). Drive this slice to a green PR. You may use subagent threads; every change MUST stay inside the allowed paths.

## Goal
Add the GATED auto-merge ACTUATOR — the module that turns a dry-run auto-merge decision into a live `enable_auto_merge(apply=True)` ONLY when every predicate re-verifies green. It must stay fully DORMANT while `run_mode == "dev"`, so the live arming flip remains a separate, Operator-RESERVED act. You build the machinery; you do NOT arm it.

## Branch
`ce-automerge-actuator` off current `origin/main` (tip 83907bb7). Fresh worktree.

## Allowed paths (HARD territory limit)
- `validators/creator_engine_validator/forge/automerge_actuator.py` (NEW)
- `validators/tests/unit/test_automerge_actuator.py` (NEW)
- `.ce/changelog/ce-automerge-actuator.md` (new)
- `.ce/pr-manifests/ce-automerge-actuator.md` (new)
Do NOT import from or touch `cred_injection_proxy.py`, `ce_egress_self_review_broker.py`, `automerge_policy.py` (read its API only), or any other file.

## Scope
Add `automerge_actuator.py` exposing a single public function:
`actuate_if_ready(decision_path, *, gh_runner) -> ActuationResult`
It must:
1. Load the dry-run decision record from `decision_path` (the JSON written by `automerge_policy.decide_automerge` / `emit_automerge_dry_run_decision`; consume the existing record shape — do not redefine it).
2. Re-verify ALL auto-predicates LIVE (do not trust the stored decision alone): `decision == AUTO`, `run_mode != "dev"`, `kill_switch == False`, `class_flag == True`, `enabling_decision_ref` present, and all `required_checks` currently green (via `gh_runner`).
3. Call `enable_auto_merge(change, apply=True)` ONLY when every predicate passes.
4. If `run_mode == "dev"`: return a `Dormant` result and touch nothing on GitHub (no gh_runner calls that mutate).
5. Fail-closed: any missing/oddly-shaped field, any failing predicate → return a refusal result, never actuate.
The run_mode flip out of `"dev"` stays as durable state owned by `automerge_policy.py` and is RESERVED to the Operator — your module only READS run_mode, never sets it.

## Tests (`test_automerge_actuator.py`)
- dormant-in-dev (run_mode dev → Dormant, gh_runner never called to mutate)
- refuse on each individually-failing predicate (decision!=AUTO, kill_switch, class_flag false, missing enabling_ref, a red required check)
- actuate-only-when-all-green (run_mode non-dev + all predicates green → enable_auto_merge(apply=True) called once) using a mock gh_runner

## Evidence (stop-line)
- FULL local preflight GREEN one pass:
  `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-automerge-actuator`
- Carriers via carrier_gen (DASHED slug); PR-manifest AND PR body carry `- **Declared work class:** story`.
- SELF-PUSH the branch as ce-dev-1 and open the PR (mention ce-ops#313/forge-autonomy; cross-repo Closes is a no-op). Then `commit && echo <SHA>` and report the PR number + head SHA.
- HARD STOP-LINE: the actuator stays DORMANT in dev; do NOT flip run_mode, do NOT trigger any live auto-merge, do NOT arm anything (RESERVED). Stay within allowed paths.
