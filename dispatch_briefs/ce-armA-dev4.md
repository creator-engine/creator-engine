# BRIEF — dev-4 — ARM-A: auto-merge actuation wiring (ce-ops#313 / arming)

Born-foreman, contained/no-egress (DO NOT push — controller harvests). Drive to READY-FOR-HARVEST.

## Goal
Wire the LIVE CALLER for the gated auto-merge actuator so auto-merge becomes ARMABLE — but it MUST stay fully DORMANT until the Operator flips run_mode. The actuator (validators/creator_engine_validator/forge/automerge_actuator.py, `actuate_if_ready(decision_path, *, gh_runner)`) already re-verifies run_mode != "dev", kill_switch, class_flag, enabling_decision_ref, and live required_checks — so wiring a caller is SAFE: it returns Dormant/Refused while run_mode=="dev". You are building the wire; the Operator arms it later by editing .ce/state/automerge/policy.json.

## SAFETY INVARIANT (non-negotiable)
- Your code MUST NOT set/flip run_mode, kill_switch, class flags, or enabling_decision_ref anywhere. Arming is the Operator's act.
- The caller must invoke the EXISTING `actuate_if_ready` (do not reimplement its predicate logic) and rely on its internal gating. Result must be a no-op (Dormant) under the current dev run_mode.

## Branch
`ce-arm-automerge-actuate` off CURRENT origin/main (git fetch origin main first). Fresh worktree.

## Scope (study first: .github/workflows/automerge-decide.yml — the existing dry-run that writes the decision JSON; automerge_actuator.py; automerge_policy.py; automerge_mutation_policy.yaml)
1. Add the LIVE CALLER as a new CI workflow `.github/workflows/automerge-actuate.yml` that runs AFTER/alongside the decision is produced (triggers on the same pull_request/merge_group events, OR workflow_run after automerge-decide), loads the decision record, and calls `actuate_if_ready(decision_path, gh_runner=<gh cli runner>)`. Least-privilege permissions, BUT sufficient for enable_auto_merge when eventually armed (contents: write / pull-requests: write — scoped to the actuate job only). The actuator's internal run_mode gate keeps it inert until armed; document that clearly in the workflow.
2. Set `required_checks` in `validators/creator_engine_validator/forge/automerge_mutation_policy.yaml` from `[]` to the real required gate: `["Validate governance artifacts"]` (so once armed, the actuator's live required-checks verification has a real check to confirm green). This is committed config; it does NOT arm anything (run_mode still dev).
3. Provide a thin caller module if needed (e.g. `validators/creator_engine_validator/forge/automerge_actuate_cli.py` or a `ce automerge-actuate` is NOT in scope — keep it to the workflow + a minimal entrypoint the workflow calls; if you add a python entrypoint that touches ce_cli.py, STOP — ce_cli.py is held by another seat; instead make the workflow call a standalone script or `python -m`).
4. Tests: a unit test proving the caller returns Dormant (no merge) when run_mode=="dev" (the safe default), and that it WOULD call enable_auto_merge only when the actuator's predicates pass (mock gh_runner + a strangeLoop decision fixture). Real asserts.

## Allowed paths (HARD limit)
- `.github/workflows/automerge-actuate.yml` (NEW)
- `validators/creator_engine_validator/forge/automerge_mutation_policy.yaml` (required_checks only)
- a NEW standalone caller module under `validators/creator_engine_validator/forge/` (if needed) + its test under `validators/tests/unit/`
- `.ce/changelog/ce-arm-automerge-actuate.md`, `.ce/pr-manifests/ce-arm-automerge-actuate.md`
Do NOT touch ce_cli.py, the broker, cred_injection_proxy, or automerge_actuator.py itself (consume it).

## Evidence (stop-line)
- FULL preflight GREEN: `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-arm-automerge-actuate`
- Carriers via carrier_gen (dashed slug); single carrier; manifest `- **Declared work class:** story` (or feature if a new workflow + module pushes the floor).
- STOP and emit: `READY-FOR-HARVEST: branch ce-arm-automerge-actuate, SHA <sha>, merge-base <mb>, changed paths: <list>, validate-pr GREEN.`
- HARD STOP-LINE: stays DORMANT under dev run_mode; you ARM nothing; no run_mode/kill_switch/class-flag/state-file edits. No push. Stay in allowed paths.
