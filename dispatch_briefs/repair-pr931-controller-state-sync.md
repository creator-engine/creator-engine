# Implementer brief — repair PR #931 controller state snapshot

## Assignment

- Ticket/work: ce-497 controller state snapshot, review repair
- PR: #931 at exact starting head `69c7fd9b55dcf7997f53aaacc8d5a388ea97d054`
- Branch: `ce-497-controller-state-sync-s1`
- Base: `origin/main@727f01a40a94f5ddcc43c52da4d0c2d31ce4718c`
- Role: `.claude/agents/implementer.md`
- Allocated worktree: `/home/ce-dev-2/creator-engine/.ce/wt-ce-497-controller-state-sync-s1-harvest`
- No network, push, PR review, approval, merge, or authority action.

## Exclusive write territory

- `tools/controller/state_sync.py`
- `validators/tests/unit/test_controller_state_sync.py`
- `.ce/changelog/ce-497-controller-state-sync-s1.md`
- `.ce/pr-manifests/ce-497-controller-state-sync-s1.md`

Read-only surrounding code is allowed.  Do not edit any other path.  Preserve
work class `story` and regenerate the carrier through the repository carrier API
if its content needs regeneration.

## Required repair

Resolve all four blocking review findings without weakening existing tests:

1. Align credential exclusion with the repository SSOT at
   `validators/creator_engine_validator/secret_paths.py`.  Snapshot collection
   must deny established credential shapes including `.env*`, `secrets/**`,
   `.ssh`, private-key basenames, `.netrc`, and `.p12`, while retaining existing
   suffix/component rules.  Add representative deny and safe-neighbor tests.
2. Fail closed on symlinks.  Neither file nor directory symlinks may enter a
   snapshot, regardless of whether the target is inside or outside the source.
   Add in-repo-secret, external-target, and directory-symlink tests.
3. Make manifest and payload a single coherent snapshot.  Refuse a non-empty
   output directory (or use an equivalently safe atomic staging design), ensure
   stale optional memory artifacts cannot survive, and copy exactly the files
   whose bytes were hashed.  Detect a source mutation between collection and
   publication and leave no apparently valid mismatched snapshot.  Test output
   reuse and mutation behavior deterministically.
4. Remove the hard-coded old controller-project slug.  Derive the default memory
   root from `--repo-root` and the current user's home, record/describe an
   override honestly, and emit portable restore instructions using an explicit
   placeholder or the recorded destination.  Tests must cover a non-default repo
   and memory root without leaking host-specific paths into instructions.

Keep dry-run as the default and do not add push or inverse-restore behavior.
Update the changelog only as needed to describe the corrected security contract.

## Validation and disk admission

Run focused tests and `git diff --check`.  Root disk is currently admission-closed
for another parity copy while ce-516 owns `/var/tmp/ce-preflight-basetemp-ce516`.
Do not begin full `ce validate-pr` until the controller explicitly sends
`PREFLIGHT-ADMISSION-OPEN`; report `READY-FOR-PREFLIGHT` after focused green and
wait.  Once admitted, use one uniquely named fixed basetemp and clean only that
basetemp after the process exits.

Standing preflight directive: run the FULL local validator preflight (`ce validate-pr`,
CI-parity) before every self-push or commit-for-harvest.  Do not discover gates via CI.

## Deliverable and stop line

After admitted full preflight is green, commit the repair with the original
dev-3 author identity and your own implementer committer identity, then report
the exact commit, changed paths, focused/full validation evidence, and residual
risk.  Do not push.  Stop on scope expansion, red validation, base/head drift,
or any requirement for credentials or controller authority.

