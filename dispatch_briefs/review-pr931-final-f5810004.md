# Reviewer brief — PR #931 final snapshot-safety head

## Assignment

- PR: #931
- Exact head: `f58100047fa286db55fc8b34fd0e078a0b6d613e`
- Prior blocked head: `b0af4185e63baf731f9fa19a25019445e9bd2759`
- Base: `origin/main@727f01a40a94f5ddcc43c52da4d0c2d31ce4718c`
- Branch: `ce-497-controller-state-sync-s1`
- Role: `.claude/agents/reviewer.md`
- Worktree: `/home/ce-dev-2/creator-engine/.ce/wt-ce-497-controller-state-sync-s1-harvest`
- Context: controller-published/self-fire; verdict cannot be APPROVE.

## Read-only review scope

- `tools/controller/state_sync.py`
- `validators/tests/unit/test_controller_state_sync.py`
- `.ce/changelog/ce-497-controller-state-sync-s1.md`
- `.ce/pr-manifests/ce-497-controller-state-sync-s1.md`
- Read-only credential-path and filesystem/security context.

Review the complete base-to-head implementation, rechecking all earlier secret,
symlink, manifest/payload, stale-output, portability, and memory-root findings.
Explicitly verify the last two TOCTOU blockers are closed:

1. Source and memory reads must be anchored to opened root descriptors and walk
   every ancestor component directory-only/no-follow before opening leaves.
   Static and concurrent ancestor symlink swaps must refuse without reading
   external bytes.
2. Output staging, content creation, cleanup, and final rename must remain
   descriptor-relative to a pinned, component-validated parent.  Static or
   concurrent parent symlink swaps must neither redirect writes nor publish an
   apparently valid snapshot.

Check descriptor lifecycle/cleanup, error paths, unsupported-platform fail-closed
behavior, memory archive creation, cross-platform flags, output naming/traversal,
and whether regression tests actually force the swaps rather than short-circuit.
Verify the changelog does not overclaim and the base-to-head carrier remains the
exact four paths.

Evidence: focused state-sync+secret-path tests 64 passed; authoritative full
wrapper PASS with baseline 7,269 passed/10 skipped/0 failed and HEAD 7,306
passed/10 skipped/0 failed; all governance gates passed; worktree clean.

Standing preflight directive: run the FULL local validator preflight (`ce validate-pr`,
CI-parity) before every self-push or commit-for-harvest.  This read-only reviewer
must not rerun mutating validator paths.

## Deliverable and stop line

Return `COMMENT` with exact evidence if no blocker is proven, or
`REQUEST_CHANGES` with file/line evidence for a blocker.  Never return or request
`APPROVE`.  Do not mutate, use network/credentials, submit a review, push,
approve, or merge.  Stop if exact head/base differs or additional authority is
required.

