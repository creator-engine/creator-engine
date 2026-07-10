ROLE: reviewer
PR: #864 reviewer-authority envelope minting
HEAD: 126c8c914fa55fcdac3283f87f6c88b113b719c5
BASE: current PR base on GitHub

Read AGENTS.md and .claude/agents/reviewer.md before acting. Work read-only.
Create an isolated review worktree, fetch PR #864, verify the live PR head is
exactly the HEAD above, and review only that head. Do not mutate GitHub, do not
approve/comment/merge/enqueue.

Bars:
- Confirm GitHub checks on the exact head are green or report BLOCKED if not.
- Confirm path manifest matches the live diff and no stale unrelated paths are
  present.
- Review reviewer-authority envelope minting behavior, launcher wiring, tests,
  and any brain/assertions ledger changes for chain consistency.
- Stop with APPROVE, REQUEST_CHANGES with findings, or BLOCKED with the exact
  blocker.

Standing preflight directive: run the FULL local validator preflight (`ce
validate-pr`, CI-parity) before every self-push or commit-for-harvest; do not
discover gates via CI. For this read-only review, do not push.
