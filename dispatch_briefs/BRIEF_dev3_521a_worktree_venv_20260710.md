# DISPATCH — dev-3 — 2026-07-10 — unit: per-worktree venv bootstrap (seat self-attest, part a) — class S
Role: implementer foreman. Signal: `READY-FOR-HARVEST ce-521a-worktree-venv-bootstrap <full-40-hex-sha>`
or `BLOCKED ce-521a-worktree-venv-bootstrap <one-line-reason>`.
Branch `ce-521a-worktree-venv-bootstrap` off freshly fetched origin/main; worktree
/var/tmp/wt-ce-521a-worktree-venv-bootstrap. SUITE POLICY: focused tests only; commit before signal.

## Context (embedded — your own seat's defect, re-scoped)
Contained seats build in per-unit git worktrees, but a fresh worktree has no working Python
interpreter for the validator package: the repo venv lives in the MAIN checkout and worktrees
don't inherit it, so in-worktree `ce validate-pr`/pytest dies (this bit your own units twice).
The repo venv itself was repaired; this unit closes the WORKTREE gap.

## Unit
A bootstrap helper `validators/creator_engine_validator/worktree_venv.py` (NEW) + a thin
invocation seam:
1. `ensure_worktree_python(worktree_root, main_repo_root)` — resolution order:
   (a) if the main repo's `.venv/bin/python` exists and imports the validator package, return
   it (worktrees SHARE the main venv via absolute path — no copy, no per-worktree venv build);
   (b) else a clear, fail-closed error naming the repair command (editable install into the
   main venv). Rationale: per-worktree venv builds burned 26G of disk in one incident — share,
   don't duplicate. Document this decision in the module docstring.
2. Make the seat-facing test-command path use it: find where the validate-pr test command
   resolves its python (CE_VALIDATOR_PYTHON env handling in pr_preflight.py) and add the
   helper as the DEFAULT resolution when CE_VALIDATOR_PYTHON is unset and the repo-root is a
   linked worktree (detect via `git rev-parse --git-common-dir` != `--git-dir`). Explicit env
   always wins. Smallest-possible integration diff.
3. Tests `validators/tests/unit/test_worktree_venv.py` (NEW): shared-venv resolution, linked-
   worktree detection, env-override precedence, fail-closed message. Plus the pr_preflight
   default-resolution seam (mock the git calls).

## Files (allowed writes)
worktree_venv.py (NEW), pr_preflight.py (minimal seam), the two test modules (one NEW, one
extended), `.ce/changelog/ce-521a-worktree-venv-bootstrap.md`, carrier (slug=branch) with
exactly `- **Declared work class:** S`. Product lens in prose.

## Stop lines
disk_headroom.py (in-flight F-1 territory — coordinate NOTHING, just don't touch), checks/**,
ce_cli.py, v3_cli.py, launch_runtime.py, release_acceptance.py, forge/**, deploy/**,
.github/**, docs/**, install.sh, docs/llms-install.md, .ce/brain/assertions.yaml.
NOTE pr_preflight.py is ALSO touched by in-flight F-1 (different region: suite-start gate).
Keep your seam surgically small; a trivial rebase conflict at harvest is acceptable, a broad
refactor is not.
