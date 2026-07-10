# BRIEF — ce-434-contained-seat-profile — validate-pr contained-seat profile (QUEUED UNIT 3)

Role: implementer (dev-4, contained, foreman mode). UNIT 3 — start after BOTH your G10 and G9
units have signaled. Branch `ce-434-contained-seat-profile` off freshly-fetched origin/main.
Worktree /var/tmp; venv `.venv/bin/python -m pytest`, PYTHONPATH=validators, TMPDIR=/var/tmp.

## Problem (embedded ticket content — you cannot read ce-ops; you LIVED this gap twice)
Contained seats (no push auth) cannot satisfy the path-manifest carrier gate: the carrier is
generated harvest-side by the controller, but `ce validate-pr` has no way to exclude that single
check. Briefs must say "full validate-pr minus the carrier check" — an instruction the tool can't
execute. Seats either stop BLOCKED with otherwise-green work (CE-410 slices 2 and 7, both dev-4)
or controllers hand-wave the bar. The seat's stop-line discipline is CORRECT; the tool must make
the correct bar expressible (bake-gaps doctrine).

## Deliverable (ticket's proposed fix)
1. `ce validate-pr --profile contained-seat` (or `--skip-check path_manifest_carrier` allowlisted
   to EXACTLY that check — pick the cleaner surface, justify in the changelog): runs the FULL
   suite minus the carrier gate and prints one line stating the omitted check and why it is
   harvest-side. Fail-closed: unknown profile/check names error; no general skip mechanism.
2. Behavioral tests: profile skips only the carrier gate (everything else still enforced +
   the notice line asserted); unknown skip target refused; default invocation byte-identical
   behavior (no profile → nothing changes).
3. Update playbooks/controller/briefs/dispatch.md to reference the real command instead of prose
   arithmetic (one short paragraph).

Files (closed set): the validate-pr entry/orchestration module(s) in
validators/creator_engine_validator/ (locate where checks are registered/sequenced; name exact
files in the carrier) · their test module(s) · playbooks/controller/briefs/dispatch.md ·
changelog · carrier (stem == branch). Do NOT touch: deploy/ (your G9/G10 units own those),
v3_cli.py review-pickup/lease regions, .github/workflows/.
⛔ signed-artifact stop-line. Preflight: FULL validate-pr (ironically — note any env-gap
false-REDs with PREFLIGHT-NOTE as usual; and yes, once this unit works you may use your own new
profile to express the carrier exclusion — say so in the signal if you do). Work class: story.
Commit `validate-pr: contained-seat profile (carrier gate is harvest-side)`, emit
`READY-FOR-HARVEST ce-434-contained-seat-profile <40-hex sha>`. Stop line: no push/PR/review/signing.
