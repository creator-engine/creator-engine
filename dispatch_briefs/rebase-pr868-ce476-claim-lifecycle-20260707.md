# Rebase brief: PR #868 ce-476-claim-lifecycle

Role: implementer.

Scope:
- Repository: `/home/cedev2/creator-engine`
- PR: `creator-engine/creator-engine#868`
- Branch: `ce-476-claim-lifecycle`
- Current PR head to start from: `0ceabebbd5cf8e9ede7fea3df0c52e36cfbd5e14`
- Target base: current `origin/main`

Context:
- Independent current-head review returned APPROVE for `0ceabebbd5cf8e9ede7fea3df0c52e36cfbd5e14`.
- dev-3 reported older READY commit `7ecc20b4c2036a4686e7dc1527d33faf212006cd`, but diagnostic confirmed it is an ancestor of current PR head. Do not harvest it.
- GitHub currently reports PR #868 as DIRTY, with no current checks.

Rules:
- You are not alone in the codebase. Do not revert or alter unrelated edits.
- Work in a new or existing isolated worktree for this branch, not the main checkout.
- Do not approve, merge, enqueue, or alter PR metadata.
- Do not dump environment variables or inspect credential configuration.
- Fetch `origin/main` and the PR branch.
- Verify branch head is still `0ceabebbd5cf8e9ede7fea3df0c52e36cfbd5e14` before rebasing. If not, stop with `HEAD_CHANGED`.
- Rebase onto current `origin/main`.
- Resolve only conflicts required by the rebase.
- Run focused validation sufficient for changed surfaces plus source `validate-pr` if feasible.
- Push only if the branch is clean, validation is green, and the rebased commit is the only intended branch movement.
- If pushing, push only to `origin/ce-476-claim-lifecycle`, then verify PR head.

Return:
- `REBASED_PUSHED`, `READY_LOCAL`, `HEAD_CHANGED`, or `BLOCKED`.
- New head SHA if produced.
- Validation run.
- Any conflicts and how they were resolved.
