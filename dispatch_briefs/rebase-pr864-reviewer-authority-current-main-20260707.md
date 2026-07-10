# Rebase repair brief: PR #864 reviewer-authority minting

Role: implementer. Write-capable only in an isolated worktree.

Repository: `creator-engine/creator-engine`
Pull request: #864
Branch: `ce-426-g11-reviewer-authority-minting`
Starting head: `58a0d0fbe8ee33da9b40853c4ede3d84452c781c`
Current PR base / `origin/main`: `5e47aeb8d94ed548f3091222798dde4e640742b2`

Problem:
- A rereview found the current live PR diff is not closed over the #864 path manifest.
- `base..HEAD` includes unrelated already-merged work from ce-475/ce-477 and other mainline changes.
- The PR must be rebased again onto current `origin/main` so the diff contains only #864 owned files.

Task:
1. Create an isolated worktree. Do not modify the controller checkout.
2. Fetch `origin/main` and `origin/ce-426-g11-reviewer-authority-minting`.
3. Verify the branch starts at `58a0d0fbe8ee33da9b40853c4ede3d84452c781c`; if not, stop `BLOCKED_HEAD_CHANGED`.
4. Rebase the branch onto current `origin/main` (`5e47aeb8d94ed548f3091222798dde4e640742b2` or newer if main advanced during fetch).
5. Resolve conflicts conservatively:
   - Preserve current main ledger entries.
   - Preserve #864 reviewer-authority evidence and manifest only.
   - Do not carry unrelated ce-475, ce-477, continuity-drill, egress-broker, README, or runbook changes in the PR diff.
   - If `.ce/brain/assertions.yaml` conflicts, recompute and verify the hash chain with repo-native brain tooling.
6. Validate:
   - `creator_engine_validator verify-path-manifest --base origin/main --manifest-dir .ce/pr-manifests --head-ref ce-426-g11-reviewer-authority-minting --require-carrier .`
   - Focused reviewer-authority tests.
   - Brain runtime/drift/hash verification if `.ce/brain/assertions.yaml` changes.
7. Push only if validation passes, using an explicit lease against `58a0d0fbe8ee33da9b40853c4ede3d84452c781c`.

Stop line:
- `REBASED_PUSHED` with new head and validation evidence, or
- `READY_BUNDLE` with bundle path/SHA/new head if you cannot push, or
- `BLOCKED` with exact reason.

Constraints:
- Do not approve, merge, enqueue, or comment on GitHub.
- Do not broaden the PR manifest beyond files actually owned by #864.
- Do not revert unrelated user/controller work.
