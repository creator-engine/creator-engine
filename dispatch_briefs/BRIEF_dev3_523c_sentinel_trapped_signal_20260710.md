# DISPATCH — dev-3 — 2026-07-10 — unit: sentinel trapped-signal deflake — class XS
Role: implementer foreman. Signal: `READY-FOR-HARVEST ce-523c-sentinel-trapped-signal-deflake <full-40-hex-sha>`
or `BLOCKED ce-523c-sentinel-trapped-signal-deflake <one-line-reason>`.
Branch `ce-523c-sentinel-trapped-signal-deflake` off freshly fetched origin/main OR LATER (>= c95c438747).
Worktree /var/tmp/wt-ce-523c-sentinel-trapped-signal-deflake. Standing preflight directive: run
`ce validate-pr --profile contained-seat` if your environment can; else focused tests +
BLOCKED(env) per protocol. PRE-SIGNAL CHECKLIST: focused tests green + confidentiality check:
`python -m pytest validators/tests/unit/test_public_docs_confidentiality.py::test_tracked_text_files_contain_no_new_confidential_or_internal_references -q`

## Context (embedded)

`validators/tests/unit/test_seat_sentinel.py::test_wrapper_trapped_signal_writes_exit[1-129]`
fails intermittently on current main — observed failing in two independent full-suite runs today
(including in a baseline run of UNMODIFIED main) while passing in others. A timing race, not a
sentinel logic defect. The parametrized case covers SIGHUP (sig 1 → exit 129); the SIGTERM case
(15 → 143) does not exhibit the flake. A sibling flake in the same file was already deflaked
(commit dd71c9cf33, "test: deflake sentinel signal exit record wait"): it replaced the
assume-written-after-wait pattern with a `_wait_for_event(sentinel, event_name)` bounded poll
(60s ceiling, 0.05s interval) with assertions unchanged. The trapped-signal test already uses
that helper yet still flakes — the remaining race is deeper: poll condition incompleteness
(event present but not yet fully written/parseable), wrapper-side emission ordering under SIGHUP,
or a race between process-group teardown and event-file I/O.

## Unit

1. Read the generated wrapper's signal-trap + exit-event emission logic in
   `validators/creator_engine_validator/seat_sentinel.py` (the trap path that emits the exit
   record for trapped signals) and the test's `_wait_for_event`/poll helpers.
2. Root-cause the residual race for the [1-129] case. Document the mechanism in the commit
   message.
3. Fix surgically: strengthen the test's poll/parse seam, or the wrapper's emission determinism
   if the race is product-side. Deterministic synchronization only — no fixed sleeps, no
   assertion weakening, no timeout inflation as the primary fix.
4. Prove stability: run the single parametrized case 30× consecutively green (pytest-repeat
   `--count=30` if available, else a shell loop; capture the tail).
5. Run the full test file once green: `python -m pytest validators/tests/unit/test_seat_sentinel.py -q`.

## Files (allowed writes)

- `validators/tests/unit/test_seat_sentinel.py`
- `validators/creator_engine_validator/seat_sentinel.py` — ONLY if the race is product-side, minimal diff
- `.ce/changelog/ce-523c-sentinel-trapped-signal-deflake.md` — changelog fragment
- `.ce/pr-manifests/ce-523c-sentinel-trapped-signal-deflake.md` — carrier (slug=branch) with exactly
  `- **Declared work class:** XS`

Product lens throughout. No internal ticket references in committed content.

## Stop lines

`.github/**`, `deploy/**`, `forge/**`, `checks/**`, `pr_preflight.py`, `ce_cli.py`, all other
in-flight modules, `.ce/brain/assertions.yaml`, brain ledger. Do not push. Do not sign.

## Signal

After focused tests pass (including the 30× loop) and the confidentiality check is green:

1. Commit all changes on branch `ce-523c-sentinel-trapped-signal-deflake`. Commit early and often.
2. Signal: `READY-FOR-HARVEST ce-523c-sentinel-trapped-signal-deflake <full-40-hex-sha>`

**In-seat validation note:** use the absolute path `/workspace/creator-engine/.venv/bin/ce` and
`/workspace/creator-engine/.venv/bin/python` — bare `ce` does not resolve correctly in the
contained seat after a relaunch.
