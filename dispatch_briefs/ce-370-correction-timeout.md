# CORRECTION — ce-ops#370 / PR #684 — bound the new network call (no-hang)

Independent review found one must-fix against the brief's explicit "never hang" requirement, plus one cheap test gap. Same branch `ce-370-local-preflight-pr-body`, same PR #684 — push onto it.

## Must-fix
1. **Bound the new `gh pr view` body-resolution call** in `validators/creator_engine_validator/pr_preflight.py` (~line 287, inside `_resolve_test_coupling_pr_body`). It currently calls `subprocess.run`/`default_runner` with NO `timeout=`. A packet-dropping firewall or stalled DNS makes `ce validate-pr` hang indefinitely — the brief required graceful degradation that NEVER hangs. Add a bounded timeout (e.g. `timeout=10`) to that gh call and catch `subprocess.TimeoutExpired` → return `None` (fail-open to the strict path, exactly like the existing non-zero-return path). The local-only flag/file paths must remain instant.

## Cheap add (do in the same push)
2. **End-to-end test for the flag exemption path:** add a test where a `--pr-body-file` containing `CE-TEST-COUPLING-EXEMPT` actually results in the coupling check being exempted (current `test_ce_validate_pr_accepts_pr_body_flags` only checks argparse population, not the exemption effect). Also assert `pr_body_file`/`pr_body` default to `None` in `test_ce_validate_pr_dispatches_to_preflight`.

## Out of scope (I'll file separately)
- The broader codebase-wide timeout policy (the existing `_fetch_base` git call also lacks a timeout) — do NOT expand into that here; just bound the ONE new gh call you added.

## Stop line
FULL `ce validate-pr` GREEN locally, push onto the existing branch (PR #684 updates), report new HEAD SHA + preflight line. A push dismisses my pending review state — that's expected; I re-review the delta.
