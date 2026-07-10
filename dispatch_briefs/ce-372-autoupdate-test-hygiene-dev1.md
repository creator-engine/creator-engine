# SEED BRIEF — ce-ops#372: auto-update P0 test-hygiene — SEAT: dev-1

**Ticket:** ce-ops#372. **Branch:** `ce-372-autoupdate-test-hygiene` (off origin/main, which now includes #682). **Role:** implementer. **Work class:** `tiny` (declare by floor).

## Goal (self-contained)
Two small test-hygiene fixes from the PR #682 review of the auto-update P0 startup notice. Both in `validators/tests/unit/test_ce_update.py`.

## Scope — exactly these two
1. **Replace the hardcoded /tmp cache path** in `test_startup_notice_prints_once_for_interactive_solo_stable` (~`test_ce_update.py:309`, the `/tmp/ce-startup-test-cache.json` literal) with pytest's `tmp_path` fixture. No real I/O happens there today (it's monkeypatched), but a hardcoded `/tmp` literal is a flakiness risk under restricted/hermetic `/tmp` in CI — use `tmp_path`.
2. **Add coverage for the uncovered branch:** a test asserting that a second `check_startup_update_notice` call, with a fresh cache where `notice_shown=True`, returns `notice_due=False` (the branch at `update.py:875-876`).

## Hard out-of-scope
Do NOT change any product logic in `update.py`/`hook_check.py`/`ce_cli.py` — this is tests-only (plus the trivial branch may need reading update.py, but do not modify it). No new features.

## Evidence / DoD
- Both tests pass; the `tmp_path` one no longer references `/tmp` literally; the new test fails if the `notice_shown` short-circuit is removed.
- Per-PR `.ce/changelog/<slug>.md` + carrier + work-class line. (Note: this is a tests-only PR — it ADDS tests, so the test-coupling gate is satisfied without an exemption.)

## Stop line
FULL `ce validate-pr` GREEN locally, push + open PR as dev-1, report SHA+PR#. Controller holds the gate.
