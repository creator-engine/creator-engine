# SEED BRIEF — D1 Forge autonomy P1: triage auto-labeling — SEAT: dev-4

**Context (self-contained):** The ce-ops triage queue (`ce_ops_triage_queue.py`, run by
`.github/workflows/ce-ops-triage-queue.yml`) now runs in APPLY mode and posts an advisory
queue table (work-class / mutation-class / lane / readiness) to a sentinel comment. It is
**advisory only — it never ratifies, approves, merges, or authorizes.** P1 extends it to
also **apply classification LABELS** to each triaged ce-ops issue, so the labels are
visible on the issues themselves (not just in one comment) — a read-only-classification
aid, fully consistent with the advisory framing.

**Branch:** `ce-triage-autolabel` (off `origin/main`).
**Role:** implementer. **Work class:** declare by diff floor (likely S).
**Repo:** creator-engine/creator-engine. Contained DGX seat: worktree under `/var/tmp`,
branch off `origin/main` (fetch first), signal READY-FOR-HARVEST when done (controller harvests).

## Goal
In `ce_ops_triage_queue.py` apply-mode, after computing each issue's classification, apply
a small, deterministic, **idempotent** label set to that ce-ops issue reflecting the
classification the queue already derives:
- work-class → `wc:XS|wc:S|wc:M|wc:L`
- readiness → `triage:ready|triage:blocked` (mirror the queue's readiness column)
- (lane/mutation optional — only if the queue already derives them cleanly; do NOT invent new taxonomies)

Requirements:
- **Idempotent**: re-running must not duplicate or thrash labels (compute desired set, diff
  vs current, add/remove only the delta within the managed `wc:`/`triage:` namespaces —
  never touch labels outside those prefixes).
- **Advisory-safe**: labeling is classification only; add NOTHING that could read as
  approval/ratification/dispatch authority. Keep the existing "advisory only" disclaimer.
- **apply-gated**: labels are written ONLY in apply mode (`--apply`); dry-run just reports
  the would-be label delta. Fail-open: a labeling error on one issue must not abort the run
  (log + continue), and must never crash the advisory-queue posting.
- **Create-missing-labels** safely (with a fixed color/description) or skip-if-absent —
  pick one, document it, keep it idempotent.

## Scope — exactly these
- `validators/creator_engine_validator/ce_ops_triage_queue.py`
- its unit tests under `validators/tests/` (add coverage: label delta computed correctly,
  idempotent re-run = no-op, dry-run writes nothing, per-issue error is isolated)
- `.github/workflows/ce-ops-triage-queue.yml` ONLY IF a new permission/label scope is
  needed (issues: write is likely already present — check first; minimize workflow churn)
- `.ce/pr-manifests/ce-triage-autolabel.md` + `.ce/changelog/ce-triage-autolabel.md`

Do NOT touch the sentinel-comment logic, the classifier itself, or anything outside triage.
Code diff with tests → test-coupling gate satisfied by your new tests.

## Evidence / DoD
- `ce validate-pr` GREEN on the DGX host venv is the controller's job at harvest; in-container just get the owned gates + targeted tests green and note any env-noise failures.
- Show a dry-run label-delta sample + an idempotency test in the report.
- Carrier stem == branch slug; regen after final commit; `rm -rf validators/build` before `git add`.
- `git commit && echo <SHA>`; signal READY-FOR-HARVEST. Do NOT push/approve/merge.
