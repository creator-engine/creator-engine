ROLE: reviewer
SEAT: dev-4
PR: #878 shape from PRD context
HEAD: 846af99a0c9f5320da9bc96d808846213e62b1c0

Read AGENTS.md and .claude/agents/reviewer.md before acting. Work read-only in
an isolated review worktree. Do not mutate GitHub, approve, merge, or enqueue.

Review bars:
- Verify live PR head is exactly HEAD above.
- Verify GitHub Validate and Advisory are green on that head, or BLOCKED if not.
- Verify path manifest matches live diff.
- Re-check prior blocker: PRD text reads must be bounded/guarded, reject unsafe
  control input as intended, and JSON/user-facing behavior remains correct.
- Stop with APPROVE, REQUEST_CHANGES with findings, or BLOCKED.

Standing preflight directive: run the FULL local validator preflight (`ce
validate-pr`, CI-parity) before every self-push or commit-for-harvest; do not
discover gates via CI. For this read-only review, do not push.
