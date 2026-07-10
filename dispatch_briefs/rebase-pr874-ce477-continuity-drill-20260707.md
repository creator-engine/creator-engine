# Rebase brief: PR #874 ce-477-continuity-drill

Role: implementer.

Scope:
- Repository: `/home/cedev2/creator-engine`
- PR: `creator-engine/creator-engine#874`
- Branch: `ce-477-continuity-drill`
- Current PR head to start from: `a94c337f4fa60b4021e2af919426d0bc9f116e18`
- Target base: current `origin/main`

Rules:
- You are not alone in the codebase. Do not revert or alter unrelated edits.
- Work in a new or existing isolated worktree for this branch, not the main checkout.
- Do not approve, merge, enqueue, or alter PR metadata.
- Fetch `origin/main` and the PR branch.
- Verify branch head is still `a94c337f4fa60b4021e2af919426d0bc9f116e18` before rebasing.
- Rebase onto current `origin/main`.
- Resolve only conflicts required by the rebase.
- Run focused validation sufficient for changed surfaces plus source `validate-pr` if feasible.
- Commit/rebase result locally only. Do not push unless the branch is clean, validation is green, and the rebased commit is the only intended branch movement.
- If pushing, push only to `origin/ce-477-continuity-drill`, then verify PR head.

Return:
- `REBASED_PUSHED`, `READY_LOCAL`, or `BLOCKED`.
- New head SHA if produced.
- Validation run.
- Any conflicts and how they were resolved.
