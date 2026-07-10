# AMENDMENT: ce-404 — pin-coupling failure is EXPECTED; hold + supersede plan

Your BLOCKED-ON-PRECURSOR was correct. The brain drift failure is the known pin-coupling class:
d1b-10/11/12-v3 (merged in #740) pin evidence_sha256 of integrator_belt.py, so YOUR edit to that
file legitimately breaks the pins. Same remedy as #740/ce-402 — but the ledger lane is serialized
and currently owned by another seat's d1b-39 supersede.

1. HOLD branch ce-404-wall-remint-on-head-mismatch at your commit 6a6a515. Do not append to the
   ledger yet. Treat this task as parked-pending-GO.
2. WHEN I SEND "GO ce-404 supersede" (precondition: the d1b-39 supersede has landed on origin/main —
   do not self-trigger): git fetch origin && merge origin/main into your branch; then via the
   documented correct_claim path append the supersede pairs for d1b-10/11/12 (active -vN → tombstone
   + -v(N+1) re-pinning integrator_belt.py's sha256 AT YOUR BRANCH HEAD); bump the drift-test
   active-count by +3 from the post-merge baseline (verify the number, don't assume); semantic-check
   the three claims still true against YOUR modified integrator_belt.py — IMPORTANT: your change
   makes head_mismatch conditionally re-mint; if any claim text (esp. d1b-12 approval-must-match-
   current-head) reads as contradicted by the new behavior, STOP and report the claim text instead
   of appending.
3. Then: regen changelog+carrier (full merge-base..HEAD path set, rm build/egg-info first), full
   ce validate-pr GREEN, commit, and report:
   `READY-FOR-HARVEST branch=ce-404-wall-remint-on-head-mismatch sha=<HEAD> preflight=PASS count=<n>`
Stop line unchanged. You may take other dispatched tasks while parked.
