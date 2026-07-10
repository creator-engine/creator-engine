# BRIEF — dev-3 — CEO-mode slice CEO-A (ce-ops#313 / forge autonomy)

You are a born-foreman builder seat (contained/no-egress; DO NOT push — the controller harvests). Drive this slice to READY-FOR-HARVEST. You may use subagent threads; every change MUST stay inside the allowed paths.

## Goal
Add the CI workflow that runs the (already-built) `ce automerge-decide` classifier on every PR and records its DRY-RUN decision as a workflow artifact / PR-check annotation. This is the forge-side observability leg of CEO-mode auto-merge: it DECIDES + RECORDS, it never MUTATES (no live merge, no arming). 

## Branch
`ce-automerge-decide-ci` off current `origin/main` (tip 83907bb7). Fresh worktree.

## Allowed paths (HARD territory limit — touch nothing else)
- `.github/workflows/automerge-decide.yml` (NEW — do NOT touch validate.yml or any existing workflow)
- `.ce/changelog/ce-automerge-decide-ci.md` (new)
- `.ce/pr-manifests/ce-automerge-decide-ci.md` (new)
No Python changes. Consume the EXISTING `ce automerge-decide` CLI subcommand (already registered in ce_cli.py) — do not modify it.

## Scope
Add `.github/workflows/automerge-decide.yml`:
- Triggers: `pull_request` (types: opened, synchronize, reopened) and `merge_group` (checks_requested).
- A job that installs/sets up the validator and runs `ce automerge-decide` for the PR (pass the PR number + head SHA + changed-paths as the existing CLI expects — inspect `ce automerge-decide --help` and the automerge_policy emit function for the exact args).
- Writes the decision JSON to `.ce/state/automerge/decisions/` and uploads it as a workflow artifact; annotate the PR check summary with the decision (AUTO/MANUAL + rationale).
- DRY-RUN / advisory ONLY: the workflow MUST NOT enable auto-merge, merge, or mutate the PR/repo. It records a decision; nothing more.
- Do NOT add any new REQUIRED check (keep the `required_checks` default from automerge_mutation_policy.yaml empty); this workflow must not block merges.

## Evidence required (stop-line)
- FULL local preflight GREEN one pass:
  `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-automerge-decide-ci`
- Carriers via carrier_gen (DASHED slug); PR-manifest carries `- **Declared work class:** story`.
- Then STOP. Emit exactly:
  `READY-FOR-HARVEST: branch ce-automerge-decide-ci, SHA <sha>, merge-base <mb>, changed paths: <list>, validate-pr GREEN.`
- DO NOT push/approve/merge. The workflow is advisory-only; no live auto-merge, no arming (RESERVED). Stay within allowed paths.
