# Seed Brief: ce-391b — _has_milestone scalar-shape fallback fix (XS, deferred minor from ce-ops#391)

- Role: implementer. Branch: `ce-391b-has-milestone-scalar` (NEW, off origin/main — fetch first;
  main must contain "share forge hold labels" #746, merged e54c21a74-era). This runs in parallel
  with your PARKED ce-404 task — keep worktrees separate; ce-404 GO still comes later.
- Worktree under /var/tmp. Venv: `.venv/bin/python -m pytest`.

## Fix (embedded — tracker unreachable)
`_has_milestone` in validators/creator_engine_validator/forge_triage.py ends in a blanket
`return True` fallback, so odd scalar shapes (non-dict/non-list milestone field values) are treated
as "has milestone" — wrong default for a triage gate. Add an explicit branch for scalar/unknown
shapes instead of blanket True (decide truthiness per the function's docstring/intent: a bare
truthy scalar like a number/string likely means a milestone reference = True; None/empty/False-y
= False; make the reasoning explicit in code, not a comment essay). Read the function and its
callers first; keep the diff surgical — that function only. NOTE: main just merged a refactor
where forge_triage.py imports shared hold labels — your base includes it; do not touch the label
logic.

## Tests
Extend the existing forge_triage tests: dict shape, list shape, None, empty string, bare string,
int — each asserting the classification outcome, not just no-exception.

## Ceremony + evidence
Changelog + carrier via carrier_gen API (rm build/egg-info first), `- **Declared work class:** XS`,
full `ce validate-pr` GREEN one pass. If the brain-drift gate fails on a forge_triage.py pin:
STOP, report BLOCKED-ON-PRECURSOR with the failing assertion ID (ledger lane is busy — do NOT
append). Commit, then exactly:
`READY-FOR-HARVEST branch=ce-391b-has-milestone-scalar sha=<HEAD> preflight=PASS`
No push, no PR actions, no ledger, no config.
