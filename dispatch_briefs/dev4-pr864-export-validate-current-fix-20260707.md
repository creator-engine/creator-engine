# dev-4 dispatch: PR #864 export and validate current fix

Role: implementer/verification in the existing contained #864 worktree.

Ticket/PR: #864 `feat(launch): in-launcher reviewer-authority envelope minting`
Branch: `ce-426-g11-reviewer-authority-minting`
Last reported contained fix commit: `9bbff9037f07a4831b8cdb4e298abfac7652ecc0`

Problem:
- The r2 worker produced a likely fix for the CI-red harness promotion matrix
  gate, but stopped `BLOCKED` because full validate-pr evidence for the final
  amended commit was unavailable.
- The host does not have object `9bbff9037f07a4831b8cdb4e298abfac7652ecc0`.
  Older host worktrees and bundle refs are stale.

Allowed surfaces:
- Existing contained #864 worktree for `ce-426-g11-reviewer-authority-minting`.
- Export artifact under `/tmp/` or `/workspace/creator-engine/tmp/` as needed.
- No unrelated branch or main-checkout edits.

Required work:
1. Locate the contained worktree that has commit
   `9bbff9037f07a4831b8cdb4e298abfac7652ecc0`.
2. Verify the worktree is clean and branch is
   `ce-426-g11-reviewer-authority-minting`.
3. Run focused checks:
   - `PYTHONPATH=validators python -m creator_engine_validator verify-harness-promotion-matrix .`
   - focused CLI tests covering the new subcommand exposure
   - path manifest fidelity gate
4. Run the FULL local validator preflight (`ce validate-pr`, CI-parity) before
   commit-for-harvest; do not discover gates via CI.
5. If full preflight passes, create a git bundle that contains the final commit
   and can be imported by the controller. Name it with the final SHA.
6. Report the exact bundle path and final SHA.

Expected evidence:
- Worktree path, branch, and `git status --short --branch`.
- Final SHA and `git log -1 --oneline`.
- Focused check results.
- Full preflight command and result.
- Bundle path and `git bundle verify` output.

Stop line:
- `READY #864 <sha> <bundle-path>` only after full preflight and bundle verify
  pass.
- `BLOCKED #864 <reason>` if the commit cannot be found, full preflight fails,
  or bundle export cannot be verified.

Hard stops:
- Do not approve, merge, enqueue, or comment on GitHub.
- Do not mutate GitHub from dev-4.
- Do not edit outside the contained #864 worktree or assigned scope.
