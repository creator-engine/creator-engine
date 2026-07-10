# BRIEF — ce-435-check-examples-fix — check-examples aggregate gate false-fail on bare origin/main (QUEUED UNIT 4)

Role: implementer (dev-1, self-push, foreman mode). UNIT 4 — start after your ce-429 PR is opened.
Branch `ce-435-check-examples-fix` off freshly-fetched origin/main.

Mandate: read ce-ops#435 directly (gh read). Deliver the fix per the ticket (FR-028: the
check-examples aggregate gate false-fails on a bare origin/main checkout across 7 fixtures).
SEMANTIC NOVELTY CHECK FIRST: reproduce the failure on your fresh checkout before fixing — if it
no longer reproduces (the libsodium/#339-adjacent work may have fixed it), signal
`BLOCKED ce-435-check-examples-fix already-resolved` with the reproduction evidence, don't build.

Files (closed set): the check-examples gate module(s) in validators/creator_engine_validator/ +
affected fixtures under examples/well-formed/ (named in carrier) + test module + changelog +
carrier (stem == branch). Do NOT touch: ce_cli.py (your ce-429 branch owns it until merged),
v3_cli.py/secret_identity.py/forge/ (dev-3), deploy/ (dev-4), .github/workflows/.
Main-vintage ce invocation for all commands. ⛔ signed-artifact stop-line. FULL validate-pr GREEN
one pass. Work class: minimal compliant. PR body: work-class line + `Closes
creator-engine/ce-ops#435`. Stop line: no review/approve/merge/enqueue. Report PR URL.
