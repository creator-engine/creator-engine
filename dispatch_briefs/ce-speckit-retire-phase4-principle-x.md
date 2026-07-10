# SEED BRIEF — Phase 4: Constitution Principle X amendment (spec-kit retirement)

**Program:** spec-kit FULL RETIREMENT (Operator-ratified 2026-06-30). **Phase:** 4 (governance-gated).
**Branch:** `ce-speckit-retire-principle-x`. **Worktree (already created, empty at origin/main):** `/home/cedev2/creator-engine/.ce/wt-principle-x`.
**Role:** implementer. **Work class:** story. **Model:** Sonnet, high effort.
**Run on the HOST venv** (governance-critical → reliability; do NOT use a contained seat). Repo root for this worktree = `/home/cedev2/creator-engine/.ce/wt-principle-x`.

## Why this phase exists
The constitution's **Principle X** currently mandates spec-kit / SDD-via-speckit compatibility. We are fully retiring spec-kit. Per the merge-order rule, this amendment must land BEFORE the mechanical removals (Phase 1 skills, Phase 2 `.specify/`) so the repo never violates its own live constitution. This is the ONLY ratification-gated phase.

## Authority / gate
- Operator has RATIFIED the amendment in principle (2026-06-30).
- **You AUTHOR it and push the branch + open the PR. You do NOT merge.** The controller holds the merge and will show the Operator the exact before/after Principle-X wording for final confirmation before merge ([[ce-authority-attaches-to-form]]).
- Record the Operator's ratification as the **Source approval** in the amendment commit/PR body (constitution amendment procedure requirement).

## Task
1. Read the current constitution: `.specify/memory/constitution.md`. Locate **Principle X** and read its exact current wording. Also read the constitution's own **amendment procedure** section and follow it exactly.
2. Draft the **minimal** amendment to Principle X: remove the spec-kit/SDD-tool mandate and reframe so CE's native `ce` (cev3) Scope-lifecycle + governed orchestration is the SDD realization (spec-kit no longer required/compatible-mandated). Do NOT rewrite unrelated principles. Keep the diff tight and surgical.
3. Apply the constitution's required **version bump**: MAJOR `1.1.0 → 2.0.0` (removing a mandated compatibility = breaking governance change). Update the version + amendment-history/ratification metadata as the constitution template requires.
4. If the amendment procedure requires a spec/plan/tasks triple, author it under `specs/` (new dir, do not touch historical `specs/00X-*`). Mirror the structure the repo already uses.
5. Run the FULL local preflight GREEN in one pass: `ce validate-pr` (use the host venv; TMPDIR=/var/tmp for a hermetic run — avoid the host `/tmp/.git` trap). Fix anything red. Two-strikes → stop and report, do not whack-a-mole.
6. Generate the PR path-manifest carrier (`carrier_gen.write_carriers(base=<merge-base>)` API — NOT hand-edit; rm any build/egg-info first) and the per-PR changelog `.ce/changelog/ce-speckit-retire-principle-x.md`. Carrier stem MUST equal the branch slug `ce-speckit-retire-principle-x`.
7. PR body MUST include exactly one `- **Declared work class:** story` line, and record the Operator Source-approval.
8. `git commit` and **echo the commit SHA**; push the branch and open the PR. Then STOP — report: the SHA, the PR number, the EXACT before/after text of Principle X (quote both verbatim so the controller can show the Operator), and the preflight result.

## Stop line
Authored + pushed + PR open + preflight GREEN + before/after Principle-X text quoted back. Do NOT merge, do NOT approve, do NOT touch Phase 1/2/3 surfaces.
