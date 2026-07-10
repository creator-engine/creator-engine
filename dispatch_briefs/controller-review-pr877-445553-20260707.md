ROLE: reviewer
PR: #877 canonical CE journey docs
HEAD: 4455537310526343fbc113320867bfa7704ccb90
BASE: current PR base on GitHub

Read AGENTS.md and .claude/agents/reviewer.md before acting. Work read-only.
Create an isolated review worktree, fetch PR #877, verify the live PR head is
exactly the HEAD above, and review only that head. Do not mutate GitHub, do not
approve/comment/merge/enqueue.

Bars:
- Confirm GitHub checks on the exact head are green; ignore stale superseded
  failed runs only if the live current head has a successful required Validate.
- Confirm path manifest matches the live diff.
- Re-review the prior requested-changes area: quickstart and guide commands
  must be pasteable, especially `ce shape` slug requirements and `ce ratify`
  approver reference, and generated HTML mirrors must match markdown sources.
- Apply night-arc tenant journey bars: no bet/appetite wording, Goal/Done-when/
  Change-type trio, Budget opt-in wording only, CLI-anchored canonical journey,
  honest loop, packs link canonical docs rather than duplicating them.
- Stop with APPROVE, REQUEST_CHANGES with findings, or BLOCKED with the exact
  blocker.

Standing preflight directive: run the FULL local validator preflight (`ce
validate-pr`, CI-parity) before every self-push or commit-for-harvest; do not
discover gates via CI. For this read-only review, do not push.
