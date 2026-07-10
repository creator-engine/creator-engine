# CI fix brief: PR #875 R4 Validate failure

Role: implementer / CI-fix worker.

Scope:
- Repository: `/home/cedev2/creator-engine`
- PR: `creator-engine/creator-engine#875`
- Branch: `ce-228-jit-cred-injection`
- Current PR head: `9da759081011af5342e81c4c78e5c88664680d88`
- Failing check: `Validate governance artifacts`, run URL from GitHub Actions at current head.
- Worktree: use `/home/cedev2/creator-engine/.ce/wt-ce-228-jit-harvest` only if its HEAD still matches the current PR head; otherwise create an isolated worktree.

Context:
- Independent review at `9da759081011af5342e81c4c78e5c88664680d88` returned APPROVE.
- GitHub Validate failed after that review, so controller approval is held.

Rules:
- You are not alone in the codebase. Do not revert or alter unrelated edits.
- Do not approve, merge, enqueue, or alter PR metadata.
- Do not dump environment variables or inspect credential configuration.
- Verify the PR head is still `9da759081011af5342e81c4c78e5c88664680d88` before editing. If not, return `HEAD_CHANGED`.
- Inspect the failing GitHub Actions log for PR #875 current head.
- If the failure is branch-scope and fixable in the #875 changed surface, apply the minimal fix locally, run focused tests and relevant validator checks, and commit locally.
- Do not push.
- If the failure is unrelated to the branch or requires a different owner, return `BLOCKED` with evidence.

Return:
- `READY`, `HEAD_CHANGED`, or `BLOCKED`.
- Root cause with log evidence.
- New local commit SHA if READY.
- Files changed.
- Tests/checks run.
