# BRIEF — dev-4 — CEO-mode slice CEO-D (ce-ops#313): automerge-status reader

Born-foreman, contained/no-egress (DO NOT push — controller harvests). Drive to READY-FOR-HARVEST. Stay in allowed paths.

## Goal
Add `ce automerge-status` — a READ-ONLY subcommand that loads the dry-run auto-merge decision records (written by the CEO-A workflow / automerge_policy) and renders a human summary (per-PR: decision AUTO/MANUAL, rationale, gate results, run_mode, class_flag, timestamps). Pure observability — it READS decision logs, never merges/mutates/arms.

## PROBE FIRST (verify-not-already-landed)
Grep ce_cli.py + forge/automerge_policy.py for an existing `automerge-status` / decision-log reader. If it already exists, STOP and report. (Note: `ce automerge-decide` already exists — do NOT touch it; you are adding a separate `automerge-status` reader.)

## Branch
`ce-automerge-status` off current `origin/main`. Fresh worktree.

## Allowed paths (HARD limit)
- `validators/creator_engine_validator/forge/automerge_policy.py` — ADD a `load_decision_records(state_dir)` helper that reads `.ce/state/automerge/decisions/*.json` and returns parsed records. Do NOT change decide_automerge / existing logic.
- `validators/creator_engine_validator/ce_cli.py` — add the `automerge-status` subcommand (parser + handler + dispatch) in the automerge section. Do NOT touch the brain group or other groups.
- `validators/tests/unit/test_automerge_status.py` (NEW)
- `.ce/changelog/ce-automerge-status.md`, `.ce/pr-manifests/ce-automerge-status.md`
Do NOT touch the broker, cred_injection_proxy, the actuator, or the decide path.

## Gate-coupling note
A new `ce` subcommand may trip a docs-reconciliation gate (test_v1_docs_reconciliation) requiring a docs/README mention. If so, add the minimal doc entry AND include that file; if the required target is outside these paths, STOP and report. `rm -rf validators/*.egg-info validators/build` before validate.

## Evidence (stop-line)
- FULL preflight GREEN: `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-automerge-status`
- Carriers via carrier_gen (dashed slug); manifest carries `- **Declared work class:** story`.
- STOP and emit: `READY-FOR-HARVEST: branch ce-automerge-status, SHA <sha>, merge-base <mb>, changed paths: <list>, validate-pr GREEN.`
- READ-ONLY observability — no merge/mutate/arm. Stay in allowed paths. No push/approve/merge.
