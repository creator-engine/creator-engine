ROLE: harvest/verification worker
PR: #878 shape from PRD context
LOCAL READY COMMIT: e9547e21852c8a9e14ac645c90a1884a58b08cb1
REMOTE CURRENT HEAD BEFORE HARVEST: 2435df3a7d018eebc9c37e8625843ccf5a23b403
DEV-3 WORKTREE: /var/tmp/ce-487-shape-from-prd-pr878 inside ce-vps-codex

Read AGENTS.md before acting. Harvest only; do not write product code beyond
mechanical harvest/rebase fixes required to preserve the ready commit.

Task:
- Verify dev-3 worktree commit exists and matches LOCAL READY COMMIT.
- Build a bundle or otherwise transfer the ready commit to controller host.
- On the controller host, fetch current main and PR #878, verify the remote PR
  is still at REMOTE CURRENT HEAD BEFORE HARVEST, rebase the ready commit onto
  the current PR branch/main as appropriate, and run a focused validation of the
  touched surfaces.
- Push with lease to PR #878 only if the head/lease still matches.
- Stop with READY_PUSHED including new head SHA and evidence, HEAD_CHANGED, or
  BLOCKED with exact blocker.

Standing preflight directive: run the FULL local validator preflight (`ce
validate-pr`, CI-parity) before every self-push or commit-for-harvest; do not
discover gates via CI. If full preflight is blocked by known host/container
environment only, include the exact blocker and the focused validation evidence
before any push.
