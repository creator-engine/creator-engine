# Rebase brief: PR #880 harness promotion parity matrix

Role: implementer. Write-capable only in an isolated worktree.

Repository: `creator-engine/creator-engine`
Pull request: #880
Branch: `ce-479-parity-matrix`
Starting head: `2534eff30a8a48d7cfe4a7b1367afb72359f6602`
Current observed base in PR metadata: `19a7f44e2259bf4b1704bd45f85804b91e7caef5`

Problem:
- PR #880 is `DIRTY` and awaits conflict resolution.
- It was previously approved and green, but now conflicts after upstream merge-queue movement.
- Known overlap area from the merge daemon: `.ce/brain/assertions.yaml`, likely with PR #874/main updates.

Task:
1. Create an isolated worktree; do not modify the controller checkout.
2. Fetch `origin/main` and `origin/ce-479-parity-matrix`.
3. Verify the branch starts at `2534eff30a8a48d7cfe4a7b1367afb72359f6602`; if not, stop `BLOCKED_HEAD_CHANGED`.
4. Rebase the branch onto current `origin/main`.
5. Resolve conflicts conservatively:
   - Preserve current main ledger entries.
   - Preserve #880 parity-matrix evidence and manifest.
   - If `.ce/brain/assertions.yaml` conflicts, recompute/verify the hash chain with repo-native brain tooling.
6. Validate:
   - `creator_engine_validator verify-path-manifest --base origin/main --manifest-dir .ce/pr-manifests --head-ref ce-479-parity-matrix --require-carrier .`
   - Focused tests for harness/parity matrix touched areas.
   - Brain runtime/drift/hash verification if `.ce/brain/assertions.yaml` changes.
7. Push only if validation passes, using an explicit lease against `2534eff30a8a48d7cfe4a7b1367afb72359f6602`.

Stop line:
- `REBASED_PUSHED` with new head and validation evidence, or
- `READY_BUNDLE` with bundle path/SHA/new head if you cannot push, or
- `BLOCKED` with exact reason.

Constraints:
- Do not approve, merge, enqueue, or mark ready.
- Do not broaden the PR manifest beyond files actually owned by #880.
- Do not revert unrelated user/controller work.
