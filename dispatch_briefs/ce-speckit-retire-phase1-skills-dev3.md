# SEED BRIEF — Phase 1: Retire spec-kit skills — SEAT: dev-3 (contained)

**Ticket/lane:** spec-kit full retirement (Operator-ratified 2026-06-30), Phase 1. **Branch:** `ce-speckit-retire-skills`. **Role:** implementer. **Work class:** tiny.

## Context (self-contained — do not need external refs)
The Operator ratified FULL RETIREMENT of spec-kit. spec-kit's runtime is redundant with CE's own `ce` (cev3) Scope lifecycle + governed orchestration. Phase 1 = remove the vendored speckit skill files. This is mechanically safe: the `skill_antidrift_guard` explicitly EXEMPTS speckit skills (they have no `ce-` prefix / `ce-internal:`/`ce-skill-class:action` markers), and no CI gate references them. Verified by prior architect analysis.

## Contained-seat mechanics (FOLLOW EXACTLY)
- Make your worktree under **/var/tmp** (NOT /workspace): `git worktree add -b ce-speckit-retire-skills /var/tmp/wt-speckit-skills origin/main` (branch off **origin/main**; if origin is stale you cannot fetch — branch off the newest local main you have and note it).
- The venv has NO activate script — run python as `.venv/bin/python -m pytest ...` and the validator via the repo's documented `ce validate-pr` entrypoint (TMPDIR=/var/tmp for a hermetic run).

## Task — delete these 13 skill directories in full
Remove every file under each of these directories:
```
.claude/skills/speckit-specify/
.claude/skills/speckit-clarify/
.claude/skills/speckit-plan/
.claude/skills/speckit-tasks/
.claude/skills/speckit-implement/
.claude/skills/speckit-analyze/
.claude/skills/speckit-constitution/
.claude/skills/speckit-checklist/
.claude/skills/speckit-git-commit/
.claude/skills/speckit-git-initialize/
.claude/skills/speckit-git-feature/
.claude/skills/speckit-git-remote/
.claude/skills/speckit-git-validate/
.claude/skills/speckit-taskstoissues/
```
(Use `git rm -r .claude/skills/speckit-*`.) Do NOT touch any `ce-*` skill (ce-dispatch, ce-harvest, ce-merge-gate, etc.) or any `.specify/` content (that is a separate phase). Do NOT modify any test file unless preflight forces it — if a test references a removed speckit skill by path and fails, report it rather than guessing; the antidrift guard should NOT fail (speckit is exempt).

## Required governance carriers
- Changelog: `.ce/changelog/ce-speckit-retire-skills.md` (one line: "Retire vendored spec-kit skill files (Phase 1 of spec-kit retirement)").
- PR path-manifest carrier: `.ce/pr-manifests/ce-speckit-retire-skills.md` — generate via the carrier_gen API (`carrier_gen.write_carriers(base=<merge-base-sha>)`); do NOT hand-edit; remove any build/egg-info first; carrier stem MUST equal branch slug `ce-speckit-retire-skills`.
- PR body must carry exactly one line: `- **Declared work class:** tiny`.

## Preflight + stop-line
- Run the FULL `ce validate-pr` to GREEN in ONE pass (TMPDIR=/var/tmp). Fix any gate (manifest/changelog/work-class). If preflight is GREEN, `git add -A && git commit` then **echo the commit SHA** (`git rev-parse HEAD`).
- STOP after commit. Report: branch, commit SHA, the final validate-pr summary line (must be GREEN), and the count of files removed. Do NOT push if you cannot reach origin — report READY-FOR-HARVEST with the SHA and the controller will harvest. If you CAN self-push, push the branch and report the pushed SHA. Do NOT open a PR, do NOT merge, do NOT approve.
