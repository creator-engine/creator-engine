ROLE: reviewer
PR: #876 CE journey next-step hints
HEAD: 2a4c86f216957c412ff2128d42dbcf6e56634f81
BASE: current PR base on GitHub

Read AGENTS.md and .claude/agents/reviewer.md before acting. Work read-only.
Create an isolated review worktree, fetch PR #876, verify the live PR head is
exactly the HEAD above, and review only that head. Do not mutate GitHub, do not
approve/comment/merge/enqueue.

Bars:
- Confirm GitHub checks on the exact head are green or report BLOCKED if not.
- Confirm PR is ready/non-draft and path manifest matches the live diff.
- Re-review the previous requested-changes area: next-step hints must not be
  unconditional, JSON next fields must be correct, and controller identity
  defaults/advisories must match the documented journey.
- Stop with APPROVE, REQUEST_CHANGES with findings, or BLOCKED with the exact
  blocker.

Standing preflight directive: run the FULL local validator preflight (`ce
validate-pr`, CI-parity) before every self-push or commit-for-harvest; do not
discover gates via CI. For this read-only review, do not push.
