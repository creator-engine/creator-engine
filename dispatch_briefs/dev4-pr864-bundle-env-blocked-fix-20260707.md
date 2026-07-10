# dev-4 dispatch: PR #864 bundle export after env-blocked preflight

Role: verification/export in the existing contained #864 worktree.

Ticket/PR: #864 `feat(launch): in-launcher reviewer-authority envelope minting`
Branch: `ce-426-g11-reviewer-authority-minting`
Contained fix commit: `9bbff9037f07a4831b8cdb4e298abfac7652ecc0`

Context:
- The prior export/validate worker reported:
  - worktree clean at `9bbff9037f07a4831b8cdb4e298abfac7652ecc0`
  - focused harness promotion command passed
  - focused CLI tests passed
  - subcommand help works
  - path manifest fidelity passed
  - full preflight failed only in broad/env gates, with zero new baseline
    failures reported:
    - portability guard literal `/run` in `container_launcher.py:86`
    - check-examples aggregate
    - well-formed examples due libsodium unavailable for Ed25519 verification
- The controller needs a harvestable bundle of this exact commit to inspect and
  decide the next #864 lane. Do not rerun full preflight unless needed for
  bundle verification.

Allowed surfaces:
- Existing contained worktree `/var/tmp/ce-426-g11-reviewer-authority-minting`.
- Export artifact under `/tmp/` or `/workspace/creator-engine/tmp/`.
- No GitHub mutation.

Required work:
1. Verify the worktree exists, is clean, and HEAD is exactly
   `9bbff9037f07a4831b8cdb4e298abfac7652ecc0`.
2. Create a git bundle containing the final branch commit(s), named with the
   final SHA.
3. Run `git bundle verify` on the bundle.
4. Report the bundle path and the exact evidence summary from the prior blocked
   preflight, making clear this is env-blocked rather than full-green.

Expected evidence:
- `git status --short --branch`.
- `git rev-parse HEAD`.
- Bundle path.
- `git bundle verify` output.
- Restated focused pass evidence and broad/env blockers.

Stop line:
- `READY-BUNDLE #864 9bbff9037f07a4831b8cdb4e298abfac7652ecc0 <bundle-path>`
  if the bundle verifies.
- `BLOCKED #864 <reason>` if the exact commit cannot be bundled or verified.

Hard stops:
- Do not approve, merge, enqueue, or comment on GitHub.
- Do not mutate GitHub.
- Do not edit files.
