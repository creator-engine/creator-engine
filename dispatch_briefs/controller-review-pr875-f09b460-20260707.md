ROLE: reviewer
PR: #875 JIT seat credential lane
HEAD: f09b460be820bb10b1754a2d205de7f59d3cb640
BASE: current PR base on GitHub

Read AGENTS.md and .claude/agents/reviewer.md before acting. Work read-only.
Create an isolated review worktree, fetch PR #875, verify the live PR head is
exactly the HEAD above, and review only that head. Do not mutate GitHub, do not
approve/comment/merge/enqueue.

Bars:
- Confirm GitHub checks on the exact head are green or report BLOCKED if not.
- Confirm PR body declares an allowed work class and path manifest matches the
  live diff.
- Review the JIT credential injection changes for credential leakage,
  revocation/TTL direction, audit coverage, and failure-direction tests.
- Stop with APPROVE, REQUEST_CHANGES with findings, or BLOCKED with the exact
  blocker.

Standing preflight directive: run the FULL local validator preflight (`ce
validate-pr`, CI-parity) before every self-push or commit-for-harvest; do not
discover gates via CI. For this read-only review, do not push.
