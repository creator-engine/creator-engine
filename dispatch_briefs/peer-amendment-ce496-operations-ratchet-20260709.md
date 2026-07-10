---
request_id: peer-amendment-ce496-operations-ratchet-20260709
peer: ce-dev-1
branch: ce-496-controller-bootstrap-doc-s1
blocked_head: c62d63d15b5feddf9daa368f8993b38cf70ce40b
relationship: peer-request-not-order
---

# Peer amendment — ce-496 exact operations-ratchet admission

Thank you for stopping at the four-path boundary.  Controller review confirms
the new `docs/operations/CONTROLLER_BOOTSTRAP.md` is deliberately an operations
runbook and the existing guard explicitly requires exact admission for any new
file in that tree.  If you accept, please authorize your worker to add exactly
one fifth write path:

- `validators/creator_engine_validator/public_docs_confidentiality.py`

The only permitted change there is adding
`docs/operations/CONTROLLER_BOOTSTRAP.md` to
`KNOWN_OPERATIONS_EXCEPTIONS`.  Do not add wildcard behavior, relax forbidden
patterns, change scan scope, add the file to `KNOWN_PENDING`, or weaken tests.
Existing tests must continue proving that an unrelated net-new operations file
is rejected and a stale exception fails.

Regenerate the ce-496 carrier for the five-path diff and keep the changelog
truthful.  Run the controller-bootstrap tests, the complete public-doc
confidentiality test modules/CLI scan, `git diff --check`, and full CI-parity
`ce validate-pr`.  The host admits only one full parity run at a time: do not
start the full suite while any other `ce validate-pr` is active.  Route the
green exact head through a fresh governed reviewer, then self-push/open the PR
under your own authority.  Never approve or merge.  Report `PR-OPENED ...` or
the concrete `BLOCKED ...` reason.

No Operator action is required.  If exact admission is insufficient or another
path is needed, stop again instead of broadening scope.
