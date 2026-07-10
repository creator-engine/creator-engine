# Seed Brief: ce-brain-chained-supersede

- Ticket: gap discovered during the ce-402 brain-drift fix (you hit it yourself: `correct_claim` refused v2→v3 with "superseded assertion must point at a currently active assertion"). A ce-ops ticket is being filed by the controller in parallel; this brief is self-contained.
- Branch: `ce-brain-chained-supersede` off `origin/main` (NEW branch — this is a PRECURSOR PR; do not put this change on ce-402-preflight-failclosed. Keep your existing /var/tmp ce-402 worktree untouched for later resume.)
- Role: implementer
- Worktree: new one under `/var/tmp`.

## The defect

`validators/creator_engine_validator/brain_runtime.py`, `_validate_current_view`
(~line 501-524): every record with `status: superseded` must have
`superseded_by` pointing at a **currently active** assertion. `correct_claim`
implements supersede by appending a tombstone record for the old id pointing at
the new id. First-level supersede (v1→v2) validates; superseding v2→v3 then
strands the old v1 tombstone (its `superseded_by` points at v2, no longer
active) and the whole ledger fails validation. Net effect: any assertion can
be corrected at most ONCE in the ledger's lifetime — chained supersede is
unrepresentable. This blocks legitimate evidence re-pins (the ce-402 case:
d1b `-v2` records need a `-v3` supersede because the evidenced file changed).

## The fix (minimal, no rule weakening beyond the chain case)

1. Relax ONLY the "currently active" target rule in `_validate_current_view`:
   a superseded record's `superseded_by` may point at a record that is itself
   superseded, PROVIDED following the `superseded_by` chain terminates at
   exactly one currently active assertion. Chain-following must be cycle-safe
   (a cycle = validation error with a clear message) and missing-target and
   ambiguity errors must stay as strict as today. Keep the existing error
   message for a chain that dead-ends in nothing active.
2. Audit `correct_claim` (~line 674-757) for any same-assumption check (e.g.
   line ~695 "assertion id is not currently active" is CORRECT and stays — you
   supersede the current ACTIVE record; do not change the append mechanics or
   record shapes).
3. Tests (add to the existing brain_runtime/drift unit-test module(s) — locate
   them with grep, e.g. `validators/tests/unit/test_ce_brain_drift.py` and any
   `test_brain_runtime*.py`): (a) v1→v2→v3 chain validates and the current
   view resolves to v3; (b) a supersede CYCLE is rejected; (c) a chain
   dead-ending in a non-existent id is rejected; (d) existing single-level
   behavior unchanged (all current tests pass unmodified).
4. Do NOT touch `.ce/brain/assertions.yaml` in this PR — no ledger content
   changes here; mechanism only.

## Allowed paths

- `validators/creator_engine_validator/brain_runtime.py`
- the existing unit-test module(s) covering it (add tests; do not delete any)
- `.ce/changelog/ce-brain-chained-supersede.md` (mandatory)
- `.ce/pr-manifests/ce-brain-chained-supersede.md` (carrier — regen via carrier_gen API, never hand-edit)

## Contained-seat mechanics

Worktree under `/var/tmp`; venv has no activate — `.venv/bin/python -m pytest`.

## Preflight (standing directive, ce-ops#303)

FULL local validator preflight (`ce validate-pr`, CI-parity) GREEN in one pass
before commit-for-harvest. Known exception: ssh-keygen install-spec gap
(ce-ops#400) — report as known exception if it is the ONLY failure.

## Work-class and changelog

`- **Declared work class:** story` likely (validator logic + 4 tests);
self-assess against the diff. Changelog fragment must state the defect (single
-level supersede cap), the relaxation's exact bound (chain must terminate at
exactly one active record, cycles rejected), and why (unblocks evidence
re-pins on assertions already at -v2).

## Stop line

- No pushes, no PR actions, no approvals, no merges, no gate/wall/daemon
  config changes, no toolchain self-update.
- No changes to ledger CONTENT (.ce/brain/assertions.yaml) or to any other
  validation rule beyond the chain-target rule described above. If the fix
  genuinely can't be bounded to that rule, STOP and report why.

## Expected evidence

- New chain/cycle/dead-end tests green + full existing suite green.
- Full preflight GREEN one pass (paste final summary line).
- `git commit && echo SHA`, then emit exactly:
  `READY-FOR-HARVEST ce-brain-chained-supersede <full-sha>`
