---
slug: ce82-lane-venv-docs
date: 2026-06-15
kind: fixed
scope: docs / lane runtime
issue: creator-engine#82
---

**CE lane / validator-test command docs no longer assume a worktree-local `.venv`.**

Isolated git worktrees under `ce-worktrees/*` carry tracked source but no local
`.venv` (it is gitignored and lives only in the canonical checkout), so lane prompts
copied from the docs could emit a worktree-relative `.venv-test/bin/python -m pytest …`
and fail with `.venv/bin/python: No such file or directory` after an otherwise-valid
lane allocation (creator-engine#82). The fix is documentation + a portable
convention — there is no generator change, because no validator code emits
`.venv/bin/python`; the assumption lived only in docs.

- Replaced the two worktree-unsafe `.venv-test/bin/python` run invocations
  (`validators/README.md`, `docs/quality/TESTING_STRATEGY.md`) with the active
  interpreter / the new convention.
- Documented the **`CE_VALIDATOR_PYTHON`** convention in `validators/README.md`:
  every sanctioned validator/test command runs `${CE_VALIDATOR_PYTHON:-python}` — the
  active interpreter by default, overridable to a known interpreter (e.g. an absolute
  canonical-checkout venv path) when a worktree has no active venv. Applied it to the
  handoff template (`templates/hermes/handoffs/HANDOFF.template.md`) and pointed the
  contributor docs (`CONTRIBUTING.md`, `docs/guide/contributing-to-ce.md`) at it.
- Added a regression-guard test
  (`validators/tests/unit/test_lane_venv_assumption.py`) that fails if any doc or
  template reintroduces a worktree-relative `.venv*/bin/python -m …` invocation.
