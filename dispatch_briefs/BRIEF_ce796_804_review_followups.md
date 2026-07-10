# BRIEF — ce-796-804-review-followups — pooled review follow-ups (TINY, dev-3)

Role: implementer (dev-3, contained). Branch `ce-796-804-review-followups` off FRESH origin/main
(fetch first; your origin/main is stale — current main HEAD is at/past fa7d7c68).
Worktree /var/tmp; venv `.venv/bin/python -m pytest`, PYTHONPATH=validators, TMPDIR=/var/tmp.

## Mandate (fully embedded — all items are non-blocking follow-ups from independent reviews)

From #796 (stale-wheel version-skew refusal gate, merged; grep for CE_ALLOW_STALE_WHEEL to find
the module and its test file):
1. Add the missing dedicated silent-path test: installed wheel versions MATCH source → the guard
   emits nothing and the command proceeds (the no-skew happy path currently lacks its own test).
   Put it in the skew guard's OWN test file — do NOT add tests to test_v3_cli.py (that file has a
   pending in-flight change parked for release; territory conflict).
2. Override-message ordering on NON-gate commands: when skew exists but the command is not a gate
   command (warn+proceed path), review found the warning/override message ordering inconsistent
   with the refusal path — make the message order consistent (versions first, then escapes), and
   pin it with an assertion in the existing warn-path test.

From #804 (contained-seat validate-pr profile, merged):
3. The profile's carrier-gate bypass matches the gate's TEXTUAL error code (exact singleton
   {path_manifest_carrier_required} set) — a fail-closed coupling to the gate's output format.
   Add a short comment AT BOTH ENDS of the coupling (where the error string is produced and where
   the profile matches it) stating: these two must change together; the bypass fails closed if
   the format drifts. Comment-only — no behavior change.

EXCLUDED from this unit (do not do): any docs-page mention of CE_ALLOW_STALE_WHEEL — that seam
belongs to an in-flight docs unit on another seat.

## STOP lines
⛔ Only: the skew guard module (item 2's message ordering), its dedicated test file (items 1-2),
the two comment sites (item 3), changelog + carrier. NO edits to test_v3_cli.py,
test_v3_installer.py, install-answers.schema.yaml, or ANY file named in docs/llms-install.md's
`_sha256:` pins (hash-pinned signed artifacts — release-op only). Never sign. No
review/approve/merge.
⚠️ Preflight caveat learned today: @requires_ssh_keygen integration tests silently SKIP in your
container — your green is NOT final; the host harvest run arbitrates. Flag in your READY note if
your run skipped tests.

## Evidence bar
Full `ce validate-pr --profile contained-seat` GREEN one pass before commit-for-harvest.
Changelog + carrier (stem == branch slug). Declared work class: tiny.
Signal: `READY-FOR-HARVEST ce-796-804-review-followups <40-hex sha>`.
