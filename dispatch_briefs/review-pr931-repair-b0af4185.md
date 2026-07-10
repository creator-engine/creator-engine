# Reviewer brief — PR #931 repaired controller-state snapshot

## Assignment

- PR: #931
- Exact repaired head: `b0af4185e63baf731f9fa19a25019445e9bd2759`
- Original reviewed parent: `69c7fd9b55dcf7997f53aaacc8d5a388ea97d054`
- Base: `origin/main@727f01a40a94f5ddcc43c52da4d0c2d31ce4718c`
- Branch: `ce-497-controller-state-sync-s1`
- Role: `.claude/agents/reviewer.md`
- Worktree: `/home/ce-dev-2/creator-engine/.ce/wt-ce-497-controller-state-sync-s1-harvest`
- Context: controller-published/self-fire; verdict cannot be APPROVE.

## Read-only review surface and required lenses

- `tools/controller/state_sync.py`
- `validators/tests/unit/test_controller_state_sync.py`
- `.ce/changelog/ce-497-controller-state-sync-s1.md`
- `.ce/pr-manifests/ce-497-controller-state-sync-s1.md`
- Read-only surrounding credential-path SSOT and filesystem/security context.

Re-review the full base-to-head change and explicitly resolve every prior
blocker:

1. Credential exclusion must align with the repository secret-path SSOT and
   established shapes without over-denying safe neighbors.
2. File and directory symlinks must fail closed for in-tree and external
   targets, without lexical/resolved-path bypass or traversal.
3. Manifest hashes and published payload must describe the same bytes;
   concurrent mutation and non-empty/stale output reuse must fail without an
   apparently valid partial snapshot.  Review staging/rename cleanup and output
   parent/path handling for traversal or symlink races.
4. Default and overridden memory roots and restore instructions must be
   portable, accurate, and free of the old controller-specific slug.

Also assess import/runtime portability of the shared secret-path policy,
regular-file/open flags across supported hosts, dry-run semantics, tar/archive
safety, error handling, and whether the new tests genuinely exercise each
boundary.  Verify exact four-path carrier fidelity and truthful changelog.

Validation evidence: state-sync tests 33 passed; combined state-sync and shared
secret-path tests 60 passed; authoritative full wrapper PASS with baseline
7,269 passed/10 skipped/0 failed and HEAD 7,302 passed/10 skipped/0 failed; all
governance gates passed; worktree clean.

Standing preflight directive: run the FULL local validator preflight (`ce validate-pr`,
CI-parity) before every self-push or commit-for-harvest.  This read-only reviewer
must not rerun mutating validator paths.

## Deliverable and stop line

Return `COMMENT` with precise evidence if no blocker is proven, or
`REQUEST_CHANGES` with exact file/line evidence for a blocker.  Never return or
request `APPROVE`.  Do not mutate, use network or credentials, submit a review,
push, approve, or merge.  Stop if exact head/base differs or authority beyond
the reviewer role is required.

