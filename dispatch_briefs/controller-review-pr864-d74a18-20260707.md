ROLE: reviewer
PR: #864 reviewer-authority envelope minting
HEAD: d74a18b71b963c90e8d6e2e78c8e9364ffe17a81

Read AGENTS.md and .claude/agents/reviewer.md before acting. Work read-only in
an isolated review worktree. Do not mutate GitHub, approve, merge, or enqueue.

Review bars:
- Verify live PR head is exactly HEAD above.
- Verify GitHub checks are green on that head, or BLOCKED if pending/failing.
- Verify path manifest matches live diff.
- Re-check prior blocker: a refused launch after `--mint-reviewer-authority`
  must not leave a valid unconsumed reviewer-authority envelope; successful
  launch consumption behavior must remain correct.
- Stop with APPROVE, REQUEST_CHANGES with findings, or BLOCKED.

Standing preflight directive: run the FULL local validator preflight (`ce
validate-pr`, CI-parity) before every self-push or commit-for-harvest; do not
discover gates via CI. For this read-only review, do not push.
