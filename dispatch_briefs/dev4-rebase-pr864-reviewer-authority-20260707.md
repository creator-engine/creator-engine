# dev-4 brief: rebase PR #864 reviewer-authority minting

Role: contained implementer worker.

Scope:
- PR: `creator-engine/creator-engine#864`
- Branch: `ce-426-g11-reviewer-authority-minting`
- Expected current head: `b3e11c58e70064517a63ef83f47081f339b94f72`
- Current state: approved but `DIRTY`; not gateable until rebased.

Rules:
- You are not alone in the codebase. Do not revert or alter unrelated edits.
- Work in an isolated worktree for `ce-426-g11-reviewer-authority-minting`, not the dirty main checkout.
- Fetch current `origin/main` and the PR branch.
- Verify branch head is still `b3e11c58e70064517a63ef83f47081f339b94f72` before rebasing. If not, report `HEAD_CHANGED`.
- Rebase onto current `origin/main`.
- Resolve only conflicts required by the rebase.
- Run focused tests for the reviewer-authority envelope/minting surface and source `ce validate-pr` if feasible.
- Commit/rebase locally and produce a verifiable commit SHA plus bundle if direct push is unavailable.
- Do not approve, merge, enqueue, sign, or change protected settings.

Stop line:
- `READY ce-426-g11-reviewer-authority-minting <sha>` if locally ready for controller harvest.
- `REBASED_PUSHED ce-426-g11-reviewer-authority-minting <sha>` only if an authorized self-push path is available and used.
- Include conflicts resolved and validation evidence.
