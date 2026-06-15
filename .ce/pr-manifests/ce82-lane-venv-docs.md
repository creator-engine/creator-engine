# PR path manifest — creator-engine#82 (lane prompts must not assume worktree `.venv`)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce82-lane-venv-docs
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below (the carrier lists itself); the fidelity scan requires the declared count and
SHA256 to match the fenced block.

Ratified scope:
creator-engine#82 in-compose BUILD MANDATE (CE-DEV-2 Controller, 2026-06-15) —
**option A approved** after the dev-1 ⏸️ escalation established that no validator code
emits `.venv/bin/python` (the assumption is documentation-resident, not a generator).
Closed manifest: fix the two stray worktree-relative `.venv-test/bin/python` doc
lines, add the `CE_VALIDATOR_PYTHON` env-var convention (default `python`) across the
validator/test-command docs + handoff template, and add the regression-guard test,
plus changelog fragment + this carrier. No generator/preflight (would be scope
growth). Untouched per the mandate constraints: `onboard_apply.py`, `v3_cli.py` apply
gate (#85, dev-2), `pco_allocator.py` (#98/#88).

Base:
`431aeff` (fresh origin/main = #227, the 0.2.0 republish with the os-native `--apply`).

Per-file purpose (the closed path-set — 8 paths):
- **`.ce/changelog/ce82-lane-venv-docs.md`** *(A)* — changelog fragment for this fix.
- **`.ce/pr-manifests/ce82-lane-venv-docs.md`** *(A)* — this carrier (self-inclusive).
- **`CONTRIBUTING.md`** *(M)* — worktree note pointing at the `CE_VALIDATOR_PYTHON`
  convention (already-safe commands left unchanged).
- **`docs/guide/contributing-to-ce.md`** *(M)* — same worktree note.
- **`docs/quality/TESTING_STRATEGY.md`** *(M)* — the stray `.venv-test/bin/python`
  test invocation → `${CE_VALIDATOR_PYTHON:-python}`.
- **`templates/hermes/handoffs/HANDOFF.template.md`** *(M)* — §8 validation-evidence
  commands → `${CE_VALIDATOR_PYTHON:-python}` + worktree note (the implementer-pane
  surface where worktree-safety matters most).
- **`validators/README.md`** *(M)* — define the `CE_VALIDATOR_PYTHON` convention;
  convert the sanctioned test invocations; fix the dev/test install block to activate
  the venv (drops the stray `.venv-test/bin/{pip,python}`).
- **`validators/tests/unit/test_lane_venv_assumption.py`** *(A)* — regression guard:
  fails if any scanned doc/template reintroduces a worktree-relative
  `.venv*/bin/python -m …` invocation; self-checks the matcher; asserts the README
  documents `CE_VALIDATOR_PYTHON`.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=ac9c74c8a1584f3beec440ff0303e8eac46083e09a584d6dde5a7d870f5371c8

```text
.ce/changelog/ce82-lane-venv-docs.md
.ce/pr-manifests/ce82-lane-venv-docs.md
CONTRIBUTING.md
docs/guide/contributing-to-ce.md
docs/quality/TESTING_STRATEGY.md
templates/hermes/handoffs/HANDOFF.template.md
validators/README.md
validators/tests/unit/test_lane_venv_assumption.py
```
