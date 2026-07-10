# SEED BRIEF — Phase 2: Retire .specify/ tree — SEAT: dev-1 (non-contained)

**Ticket/lane:** spec-kit full retirement (Operator-ratified 2026-06-30), Phase 2. **Branch:** `ce-speckit-retire-specify`. **Role:** implementer. **Work class:** tiny.

## Context (self-contained)
The Operator ratified FULL RETIREMENT of spec-kit. Phase 2 = remove the vendored `.specify/` tree (templates, scripts, extensions, integrations, workflows, config) — EXCEPT the constitution, which is governance-gated and stays. No CI gate scans `.specify/`; removal is mechanically safe (verified by prior architect analysis).

## Task — delete the `.specify/` tree EXCEPT the constitution
Remove all of `.specify/` EXCEPT `.specify/memory/constitution.md` (KEEP that one file — it is the constitution governance artifact; its Principle X is amended in a separate ratification-gated phase, not here).
Concretely remove:
```
.specify/extensions/        (all ~14 files)
.specify/integrations/      (claude.manifest.json, speckit.manifest.json, codex.manifest.json)
.specify/scripts/           (bash/ helpers: check-prerequisites, common, create-new-feature, setup-plan, setup-tasks)
.specify/templates/         (checklist-, constitution-, plan-, spec-, tasks-template.md)
.specify/workflows/         (speckit/workflow.yml, workflow-registry.json)
.specify/extensions.yml
.specify/feature.json
.specify/init-options.json
.specify/integration.json
```
KEEP: `.specify/memory/constitution.md`. Do NOT touch `.claude/skills/` (separate phase) or any `docs/` (separate phase). Use targeted `git rm` per path; verify `.specify/memory/constitution.md` still present after.

## Required governance carriers
- Changelog: `.ce/changelog/ce-speckit-retire-specify.md` ("Retire .specify/ tree except constitution (Phase 2 of spec-kit retirement)").
- PR path-manifest carrier: `.ce/pr-manifests/ce-speckit-retire-specify.md` — generate via carrier_gen API (`carrier_gen.write_carriers(base=<merge-base-sha>)`); no hand-edit; rm build/egg-info first; stem == branch slug `ce-speckit-retire-specify`.
- PR body line: `- **Declared work class:** tiny`.

## Mechanics + preflight + stop-line
- Branch off current `origin/main` (you are non-contained — fetch first): `git fetch origin && git worktree add -b ce-speckit-retire-specify <wt-path> origin/main`.
- Run FULL `ce validate-pr` GREEN in ONE pass (TMPDIR=/var/tmp). Fix any gate. Confirm NO gate fails on the removal (none should — `.specify/` is unscanned).
- Commit, then **self-push** the branch `ce-speckit-retire-specify` (you can self-push). Echo the pushed HEAD SHA. Do NOT open a PR, merge, or approve — report READY with the branch + SHA + final validate-pr summary line; the controller opens/gates the PR.
