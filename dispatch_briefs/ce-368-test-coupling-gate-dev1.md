# SEED BRIEF — #368: validate-pr CE-native test-coupling gate — SEAT: dev-1 (non-contained)

**Ticket:** ce-ops#368 (CE-native test-coupling gate). **Branch:** `ce-368-test-coupling-gate`. **Role:** implementer. **Work class:** declare by floor (likely `story`).

## Goal (self-contained — embed, do not rely on reading the private ticket)
Add a `ce validate-pr` check that flags a PR whose diff adds/changes **code** (non-test source) but adds **no new tests**. This is the "grader outside the agent" enforcing test-first coupling — CE-native, NOT from spec-kit. It is a FINDING-level gate consistent with the existing work-sizing floor pattern.

## Design constraints
- Implement as a new check module under `validators/creator_engine_validator/checks/` (mirror the structure/registration of a sibling check, e.g. how `skill_antidrift_guard.py` or the work-sizing floor is wired). Reuse the existing PR-diff machinery (`_pr_diff_ceiling_stats` / the base-comparison helpers used by `verify-work-sizing-floor`) for computing added/changed files vs a base — DO NOT reinvent diffing.
- Definition of "code": added or modified lines in non-test source files (e.g. `validators/creator_engine_validator/**/*.py` excluding `tests/`, and other first-class source dirs). "Test": files under a `tests/` path or matching `test_*.py` / `*_test.py`.
- Trigger: if the diff has code changes above a small threshold AND zero new/changed test files → emit a FINDING (fail or advisory — match the severity convention of the work-sizing floor; prefer a blocking finding for `code` mutation_class, with a documented opt-out marker in the PR body for legitimately test-exempt changes, mirroring how other gates allow a declared override). Pure-docs / pure-deletion / config-only diffs must NOT trip it.
- Wire it into the validate-pr aggregate AND the forge `validate.yml` path if that's where sibling gates run. Add unit tests under `validators/tests/unit/` covering: code+no-test → finding; code+test → pass; docs-only → pass; deletion-only → pass; opt-out marker → pass.

## Mechanics (non-contained seat — you self-push)
- Worktree off `origin/main`: `git worktree add -b ce-368-test-coupling-gate <path> origin/main`.
- Run FULL `ce validate-pr` GREEN locally in one pass before pushing (TMPDIR=/var/tmp; avoid host /tmp/.git trap). Two-strikes → consult SSOT, don't whack-a-mole.
- Add a per-PR changelog `.ce/changelog/ce-368-test-coupling-gate.md` and regenerate the path-manifest carrier via `carrier_gen.write_carriers(base=<merge-base>)` (stem == branch slug; rm build/egg-info first).
- New top-level behavior: ensure docs reconciliation passes — if you add a new `ce` subcommand or change documented behavior, update the relevant README/docs the test expects (run the full suite; it'll tell you).
- PR body: exactly one `- **Declared work class:** <class>` line (use the floor-satisfying class from `verify-work-sizing-floor`).
- `git commit && echo <SHA>`, push, open the PR. STOP and report PR #, SHA, preflight result, and the test list. Do NOT approve/merge.

## Stop line
PR open + full preflight GREEN + unit tests for all 5 cases + carrier/changelog present. Nothing merged.
