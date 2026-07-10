ROLE: implementer
SEAT: dev-4
PR: #864 reviewer-authority envelope minting
HEAD REVIEWED: 126c8c914fa55fcdac3283f87f6c88b113b719c5

Read AGENTS.md and .claude/agents/implementer.md before acting. You are not
alone in the codebase; do not revert others' edits. Work in an isolated
worktree for PR #864. Do not approve, merge, or enqueue.

Blocking reviewer finding to repair:
- `validators/creator_engine_validator/lane_runtime.py` writes the minted
  reviewer-authority envelope before later launch refusal gates run.
- Reproduction: launch with `--mint-reviewer-authority` and unavailable tmux
  adapter raises `G3-TMUX-UNAVAILABLE`, but leaves
  `.hermes/active-work-ledger/panes/cid/lid.reviewer-authority.yaml` present
  with `consumed_at=None` and a future `expires_at`.
- This violates `docs/operations/GOVERNED_LANE_LAUNCH_PROTOCOL.md`, which says
  refusals happen before side effects and the first successful venue launch
  consumes the grant.

Expected fix:
- Reorder mint/write so refused launches do not leave a valid unconsumed
  reviewer-authority artifact.
- Preserve the intended successful-launch consumption behavior.
- Add focused regression coverage for unavailable tmux/refusal with
  `--mint-reviewer-authority` proving no envelope remains, plus successful path
  coverage if needed.

Bars:
- Keep scope to #864 surfaces and required tests/carriers/changelog.
- Run focused reviewer-authority tests and full `ce validate-pr` before
  commit-for-harvest or self-push.
- Stop with READY <head> plus bundle or pushed head evidence, or BLOCKED with
  exact blocker.

Standing preflight directive: run the FULL local validator preflight (`ce
validate-pr`, CI-parity) before every self-push or commit-for-harvest; do not
discover gates via CI.
