# Rebase brief: PR #875 JIT credential lane current-main sync

Role: implementer. Write-capable only in an isolated worktree.

Repository: `creator-engine/creator-engine`
Pull request: #875
Branch: `ce-228-jit-cred-injection`
Starting head: `e32231645482b1bb695087a7fa80caf7c0b67e80`
Current observed PR base: `b935777ce84730d66d5e4f7d52dde92bd01b4169`
Current main observed by controller: `5e47aeb8d94ed548f3091222798dde4e640742b2`

Problem:
- The PR body was corrected from `story`/S to `feature`/M after a work-sizing failure.
- A rerun of the old pull_request event still used the stale event payload and failed with `Declared work class: S`.
- A separate fresh validation passed, but the stale failing check remains in the PR rollup.
- Main has also advanced since the current head was pushed.

Task:
1. Create an isolated worktree. Do not modify the controller checkout.
2. Fetch `origin/main` and `origin/ce-228-jit-cred-injection`.
3. Verify the branch starts at `e32231645482b1bb695087a7fa80caf7c0b67e80`; if not, stop `BLOCKED_HEAD_CHANGED`.
4. Rebase onto current `origin/main`.
5. Preserve the existing #875 code changes and manifest only. Do not reintroduce unrelated ce-481 paths.
6. Validate:
   - PR body declares `feature` on GitHub.
   - `creator_engine_validator verify-path-manifest --base origin/main --manifest-dir .ce/pr-manifests --head-ref ce-228-jit-cred-injection --require-carrier .`
   - Focused tests for JIT credential lane / egress broker changes.
   - `creator_engine_validator check $(git diff --name-only origin/main...HEAD)`.
7. Push only if validation passes, using an explicit lease against `e32231645482b1bb695087a7fa80caf7c0b67e80`.

Stop line:
- `REBASED_PUSHED` with new head and validation evidence, or
- `READY_BUNDLE` with bundle path/SHA/new head if you cannot push, or
- `BLOCKED` with exact reason.

Constraints:
- Do not approve, merge, enqueue, or comment on GitHub.
- Do not broaden the PR manifest.
- Do not revert unrelated user/controller work.
