# BRIEF — dev-1 — Forge-side epic slice FORGE-6 (ce-ops#34): ratification-gated workflow registry

Born-foreman, non-contained (SELF-PUSH as ce-dev-1). Drive to a green PR. Stay in allowed paths.

## IMPORTANT: branch off CURRENT origin/main
Run `git fetch origin main` and create the worktree off `origin/main` (NOT local main — stale local main causes phantom-diff pollution).

## Goal
Add the data-layer that backs the workflow-catalog (#634, merged) with RATIFICATION GATING: a registry of named governed workflows, each carrying a ratification status, with a query API so the forge can answer "is workflow X ratified for autonomous use?" This is advisory/read-model data + queries — it does NOT execute workflows or mutate anything.

## PROBE FIRST (verify-not-already-landed)
Grep `validators/creator_engine_validator/forge/` for an existing workflow registry/ratification module. If one exists, STOP + report.

## Branch
`ce-forge-workflow-registry` off current `origin/main`. Fresh worktree.

## Allowed paths (HARD limit)
- `validators/creator_engine_validator/forge/workflow_registry.py` (NEW) — a self-contained module: load the named workflows (mirror the entries in `docs/contracts/workflow-catalog.md` — define them as structured constants in the module, keyed by name with fields name/purpose/classification/ratified:bool), expose `is_ratified(name) -> bool` (default False / fail-closed for unknown or unratified), `list_workflows()`, `get_workflow(name)`. NO execution, NO network, NO mutation, NO imports from ce_cli/broker/cred_proxy/automerge. Ratification status is durable data (default unratified — flipping a workflow to ratified is an Operator act, out of scope here).
- `validators/tests/unit/test_workflow_registry.py` (NEW)
- `.ce/changelog/ce-forge-workflow-registry.md`, `.ce/pr-manifests/ce-forge-workflow-registry.md`
Do NOT touch ce_cli.py (another seat is editing it), the broker, or any other module. NO docs file (this is a code module; if a gate demands a doc, STOP + report rather than expand scope).

## Tests
- is_ratified returns False for unknown names (fail-closed) and for unratified workflows; True only for any explicitly-ratified entry (if you seed none as ratified, test that all default False — that's correct + safe).
- list_workflows / get_workflow return the catalog entries; get_workflow raises/None on unknown.
- Registry entries match the workflow-catalog names.

## Evidence
- FULL preflight GREEN: `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-forge-workflow-registry`
- Carriers via carrier_gen (dashed slug); single carrier; manifest+body `- **Declared work class:** story`.
- SELF-PUSH as ce-dev-1, open PR (mention ce-ops#34), report PR# + SHA. Fail-closed default-unratified; no execution/mutation. No approve/merge. Stay in allowed paths.
