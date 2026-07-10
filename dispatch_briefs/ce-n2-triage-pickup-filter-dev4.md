# SEED BRIEF — N2 forge-driving: triage ready-to-dispatch pickup filter — SEAT: dev-4

**Context (self-contained):** The ce-ops triage queue (`ce_ops_triage_queue.py`) already
classifies each issue (work-class, mutation-class, lane, readiness via
`forge_triage.readiness_blockers`) and posts an advisory queue + labels. It does NOT yet
emit a **machine-readable "ready-to-dispatch" candidate list** — the pickup filter that a
controller/conveyor can consume to pick the next dispatchable work. Build that (advisory
output only; this does NOT auto-dispatch to seats — that stays controller-gated).

**Branch:** `ce-n2-triage-pickup-filter` (off `origin/main`). **Role:** implementer. **Work class:** by floor (likely S/M).
**Repo:** creator-engine/creator-engine. Contained DGX seat: worktree `/var/tmp`, branch off origin/main (fetch first), READY-FOR-HARVEST when done.

## Goal
Add a pure function + a `--emit-pickup <path>` (or JSON stdout) mode to the triage queue
that outputs the **dispatch-candidate list**: issues that are `readiness == ready`
(no blockers), NOT already assigned/in-progress, with their work-class/lane/mutation-class,
sorted by a deterministic priority (e.g. lane then work-class then issue number). Value-free
(issue numbers/labels only; no secrets). Keep it **advisory** — reuse the existing
`NON_AUTHORITY_STATEMENT`; the output must NOT read as authorizing dispatch, only listing
candidates. It must NOT open PRs, dispatch, label-mutate beyond what #713 already does, or
merge.

## Scope — exactly these
- `validators/creator_engine_validator/ce_ops_triage_queue.py` (add the pickup-filter
  function + the emit mode; reuse existing classification/readiness helpers — do NOT
  duplicate forge_triage logic).
- `validators/tests/unit/test_ce_ops_triage_queue.py` (tests: ready+unblocked+unassigned
  included, blocked/assigned excluded, deterministic ordering, dry-run/no-mutation, empty set).
- `.ce/pr-manifests/ce-n2-triage-pickup-filter.md` + `.ce/changelog/ce-n2-triage-pickup-filter.md`
Do NOT touch conveyor*, pr_preflight, ce_brain_drift, ce_cli group registration (no new CLI
group — add it as a mode/flag on the EXISTING triage entrypoint to avoid docs-reconciliation coupling). Code+tests → coupling satisfied.

## Evidence / DoD
- Owned gates + targeted tests GREEN in-container; controller runs full validate-pr on DGX host venv (PYTHONPATH=validators) at harvest.
- Show the pickup-filter test (ready included / blocked excluded / ordering) in your report.
- Carrier stem == branch slug; regen after final commit; `rm -rf validators/build` before `git add`.
- `git commit && echo <SHA>`; READY-FOR-HARVEST. Do NOT push/approve/merge.
