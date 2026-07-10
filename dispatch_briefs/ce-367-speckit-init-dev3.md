# SEED BRIEF — ce-ops#367 (P0 slice): `ce speckit init` scaffold — SEAT: dev-3

**Context (self-contained — embed):** Fresh external users who install CE and point it at
their own project cannot discover/run any `/speckit-*` commands, because the `.specify/`
tree + speckit skills are checked into the creator-engine repo ONLY and never scaffolded
into user projects. `ce init` writes only `.hermes/`; greenfield/brownfield scaffolds
write only gitignore/README/`.ce/skills/*`. **No `ce speckit init` command exists.** Build
a bounded P0: a `ce speckit init` command that scaffolds the `.specify/` tree + the speckit
skill artifacts into a target project directory.

**Branch:** `ce-367-speckit-init` (off `origin/main`). **Role:** implementer. **Work class:** by floor (likely S/M).
**Repo:** creator-engine/creator-engine. Contained VPS seat: worktree `/var/tmp`, branch off origin/main (fetch first), READY-FOR-HARVEST when done.

## P0 Goal (bounded — do NOT try to solve every layer of the ticket)
Add `ce speckit init [--target <dir>] [--force]` that:
1. Scaffolds the canonical `.specify/` tree into the target project (default = cwd). Source the canonical structure/templates from what already exists in THIS repo's `.specify/` (read it: `git show origin/main:.specify/...` / `ls .specify`). Copy the reusable template/command files a user project needs — NOT repo-internal state.
2. Idempotent + safe: if `.specify/` already exists, do NOT clobber unless `--force`; print what it created/skipped. Never overwrite user edits silently.
3. Distributes the speckit skill artifacts the same way the brownfield scaffold delivers `.ce/skills/*` (mirror that pattern — grep `BROWNFIELD_SKILL_ARTIFACT_PATHS` in v3_installer.py for the convention).
4. Value-free, path-only; no secrets, no network.

## Scope — keep tight
- `validators/creator_engine_validator/ce_cli.py` (register `speckit init` subcommand; mirror an existing group's arg style + update the top-of-file help block).
- a new small module for the scaffold logic (e.g. `validators/creator_engine_validator/speckit_init.py`) — pure/testable (inject the target path + a file-writer; no direct cwd side-effects in the core).
- **NEW ce CLI group → docs coupling:** a new top-level `ce` group trips `test_v1_docs_reconciliation` — update README.md's command list + that test accordingly ([[ce-new-ce-group-docs-coupling]]).
- tests under `validators/tests/` (scaffold creates expected files, idempotent no-clobber, --force overwrites, missing-target errors cleanly).
- `.ce/pr-manifests/ce-367-speckit-init.md` + `.ce/changelog/ce-367-speckit-init.md`.
Do NOT touch ce_brain_drift.py, pr_preflight.py, conveyor*, deploy/queue-daemon/* (parallel lanes own those). Code diff with tests → coupling satisfied.

## Evidence / DoD
- Owned gates + targeted tests GREEN in-container (esp. test_v1_docs_reconciliation); note env-noise; controller runs full validate-pr on DGX host venv (PYTHONPATH=validators) at harvest.
- Show a scaffold-into-tmpdir test + the idempotency test in your report.
- Carrier stem == branch slug; regen after final commit; `rm -rf validators/build` before `git add`.
- `git commit && echo <SHA>`; READY-FOR-HARVEST. Do NOT push/approve/merge.
