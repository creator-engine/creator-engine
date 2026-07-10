# Rebase brief: PR #875 ce-228-jit-cred-injection R5

Role: implementer.

Scope:
- Repository: `/home/cedev2/creator-engine`
- PR: `creator-engine/creator-engine#875`
- Branch: `ce-228-jit-cred-injection`
- Current PR head to start from: `9da759081011af5342e81c4c78e5c88664680d88`
- Target base: current `origin/main`

Context:
- Independent current-head review returned APPROVE for `9da759081011af5342e81c4c78e5c88664680d88`.
- GitHub Validate failed because path-manifest verification against live base sees unrelated ce-481 deletions:
  - `.ce/changelog/ce-481-signing-deputy-design.md`
  - `.ce/pr-manifests/ce-481-signing-deputy-design.md`
  - `docs/design/sshsig-signing-deputy.md`
- Do not add those unrelated paths to the #875 manifest. The likely fix is rebasing/restoring current base state so #875 no longer deletes unrelated ce-481 files.

Rules:
- You are not alone in the codebase. Do not revert or alter unrelated edits.
- Work in `/home/cedev2/creator-engine/.ce/wt-ce-228-jit-harvest` only if it is clean and at the expected head; otherwise create an isolated worktree.
- Do not approve, merge, enqueue, or alter PR metadata.
- Do not dump environment variables or inspect credential configuration.
- Fetch `origin/main` and the PR branch.
- Verify branch head is still `9da759081011af5342e81c4c78e5c88664680d88` before rebasing. If not, stop with `HEAD_CHANGED`.
- Rebase onto current `origin/main`.
- Preserve unrelated ce-481 files from current base; do not include them in #875's manifest.
- Regenerate or adjust #875 carriers only as needed to match the actual #875 diff.
- Run focused tests plus source validator checks, including path-manifest verification against live base.
- Push only if the branch is clean, validation is green, and the rebased commit is the only intended branch movement.
- If pushing, push only to `origin/ce-228-jit-cred-injection`, then verify PR head.

Return:
- `REBASED_PUSHED`, `READY_LOCAL`, `HEAD_CHANGED`, or `BLOCKED`.
- New head SHA if produced.
- Validation run.
- Any conflicts and how they were resolved.
