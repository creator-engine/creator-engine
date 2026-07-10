# Reviewer brief — ce-516 Item 3 brain-window harvest

## Assignment

- Ticket/work: ce-516 Item 3 workflow comment and record-65 correction
- Exact head: `5f837c1be4a44bfd3d15c45e94ad76ae038121a5`
- Base: `origin/main@727f01a40a94f5ddcc43c52da4d0c2d31ce4718c`
- Branch: `ce-516-item3-brain-window`
- Role: `.claude/agents/reviewer.md`
- Worktree: `/home/ce-dev-2/creator-engine/.ce/wt-ce-516-item3-brain-window`
- Review context: controller-published/self-fire; verdict cannot be APPROVE.

## Read-only review surface

- `.github/workflows/ce-ops-autoclose.yml`
- `.ce/brain/assertions.yaml`
- `validators/tests/unit/test_ce_brain_drift.py`
- `.ce/changelog/ce-516-item3-brain-window.md`
- `.ce/pr-manifests/ce-516-item3-brain-window.md`
- Read-only surrounding ledger/schema/workflow context needed to verify the chain.

Verify that the workflow change is comment-only and exactly correct, with no
permission/trigger/job/logic drift.  Recompute its SHA-256 and require
`ed1be82ac0a735fc4155633135ff2fdc25488c5bedf0c612041fb1d46ddae486`.
Verify the ledger correction was produced as a chain-safe supersession of
`brain-assertion-d1b-16-cross-repo-closes-bot-v2` by active v3, preserving the
statement/claim except the new evidence hash; require 165 records, 105 active,
tail sequence 164, and no second chain.  Verify the test ratchet, carrier, and
changelog are truthful and the base-to-head diff is exactly the five paths.

Existing evidence: focused brain-drift tests 31 passed; full CI-parity preflight
green with baseline and HEAD each 7,269 passed and 10 skipped; worktree clean.

Standing preflight directive: run the FULL local validator preflight (`ce validate-pr`,
CI-parity) before every self-push or commit-for-harvest.  This read-only reviewer
performs neither and must not run a validator path that mutates scratch/worktrees.

## Deliverable and stop line

Return `COMMENT` with concise evidence if no blocker is proven, or
`REQUEST_CHANGES` with exact file/record evidence for a blocker.  Never return or
request `APPROVE`.  Do not mutate, use network or credentials, submit a review,
push, approve, or merge.  Stop if the exact head/base differs or the review would
require authority outside the reviewer role.

