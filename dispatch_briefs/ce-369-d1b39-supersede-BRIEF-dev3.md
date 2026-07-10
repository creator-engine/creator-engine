# Seed Brief: ce-369 — d1b-39 supersede (unblocks your BLOCKED-ON-PRECURSOR)

- Role: implementer. Your precursor is RESOLVED: PR #740 merged to main (merge commit 026ec6e7c,
  ledger now at 76 active records incl. the d1b-10/11/12 -v3 chain). The ledger lane is yours now —
  this is the ONLY in-flight PR allowed to touch .ce/brain/assertions.yaml.
- Branch: `ce-369-denylist-from-ssot` (EXISTING — your /var/tmp worktree, head 858a15e9 or later).
  Original brief /var/tmp/ce-369-denylist-from-ssot-BRIEF.md still governs the overall ticket;
  this brief adds the supersede step you reported as the only remaining drift.

## Steps
1. `git fetch origin` then merge origin/main into the branch (must bring 026ec6e7c; verify
   `git merge-base --is-ancestor 026ec6e7c HEAD` after the merge). If the merge conflicts on
   assertions.yaml, resolve by keeping BOTH main's appends and your branch's (append-only union,
   main's records first); any other conflict → STOP and report BLOCKED with the conflict paths.
2. Walk the d1b-39 chain in .ce/brain/assertions.yaml to find its ACTIVE record (whatever -vN it
   is after the merge). Via the documented `correct_claim` path, append the supersede pair:
   tombstone for the active record + new -v(N+1) re-pinning `evidence_sha256` of pyproject.toml
   to its sha256 at YOUR branch head (your branch modifies pyproject.toml — that is the expected
   drift you observed). Semantic-check the claim statement still true at your head; if the claim
   text itself is stale beyond the pin, STOP and report rather than rewriting doctrine.
3. Bump the active-count assert in validators/tests/unit/test_ce_brain_drift.py by +1 (76→77 —
   verify 76 is the post-merge baseline first; if different, recompute and report the number).
4. Regenerate changelog fragment + carrier for the FULL merge-base..HEAD path set via the
   carrier_gen.write_carriers API (rm build/ and *.egg-info first; never hand-edit).
5. FULL `ce validate-pr` GREEN in one pass (ssh-keygen known-exception rule applies: report it
   if it is the ONLY failure). Then `git commit && echo SHA`.

## Evidence + stop line
- Report exactly: `READY-FOR-HARVEST ce-369-denylist-from-ssot <full-sha> preflight=<PASS|PASS-except-sshkeygen> count=<new-active-count>`
- NO push, NO PR actions, NO other ledger edits beyond the one d1b-39 supersede pair, NO config.
  Stop after the done-report. Your ce-391 task continues in parallel — keep the two worktrees
  strictly separate.
