# Harvest brief: PR #868 ce-476-claim-lifecycle

Role: implementer/harvest worker.

Scope:
- Worktree: `/home/cedev2/creator-engine/.ce/wt-ce476-r3-harvest`
- Expected local HEAD: `0ceabebbd5cf8e9ede7fea3df0c52e36cfbd5e14`
- Target remote branch: `origin/ce-476-claim-lifecycle`
- PR: `creator-engine/creator-engine#868`

Rules:
- You are not alone in the codebase. Do not revert, rewrite, or repair unrelated work.
- Do not edit files.
- Do not approve, merge, enqueue, or alter PR metadata.
- Verify the worktree is clean and HEAD exactly matches the expected SHA before any push.
- Verify the current remote branch head before pushing.
- Push only the expected commit/ref to `origin/ce-476-claim-lifecycle`.
- After push, verify `gh pr view 868 --repo creator-engine/creator-engine --json headRefOid` reports the expected SHA.

Return:
- `HARVESTED` or `BLOCKED`.
- Remote head SHA after push.
- Commands run and any notable warnings.
