# Implementer amendment — PR #931 ancestor-symlink TOCTOU

## Assignment

- PR: #931
- Starting head: `b0af4185e63baf731f9fa19a25019445e9bd2759`
- Base: `origin/main@727f01a40a94f5ddcc43c52da4d0c2d31ce4718c`
- Branch: `ce-497-controller-state-sync-s1`
- Role: `.claude/agents/implementer.md`
- Worktree: `/home/ce-dev-2/creator-engine/.ce/wt-ce-497-controller-state-sync-s1-harvest`
- Full-preflight admission: CLOSED while ce-496 owns the host slot.

## Exclusive write territory

- `tools/controller/state_sync.py`
- `validators/tests/unit/test_controller_state_sync.py`
- `.ce/changelog/ce-497-controller-state-sync-s1.md`
- `.ce/pr-manifests/ce-497-controller-state-sync-s1.md` only if carrier regeneration is needed

No other path.  No network, credentials, push, review, approval, or merge.

## Blocking repair

The prior use of `O_NOFOLLOW` protects only the final pathname component and is
insufficient.  Repair both boundaries without weakening the earlier fixes:

1. Source reads must be anchored to an opened source-root directory descriptor.
   Walk every relative ancestor component with descriptor-relative `openat`
   semantics (`dir_fd`, directory-only, no-follow), then open the leaf relative
   to the pinned parent descriptor with no-follow.  A static or concurrent
   ancestor replacement by a symlink must be refused; external bytes must never
   be hashed or copied.  Apply the same rule to the optional memory root.
2. Output publication must pin the real output parent directory descriptor after
   component-by-component no-follow traversal.  Create staging content and the
   final rename relative to that descriptor.  Do not use an attacker-swappable
   pathname for `mkdir`, file creation, cleanup, or rename after the parent is
   pinned.  A pre-existing parent symlink and a parent swap before publication
   must refuse without writing outside the authorized parent.
3. Keep manifest-driven byte verification, non-empty-output refusal, atomic
   staging, dry-run default, secret-path SSOT alignment, portable memory-root
   instructions, and safe cleanup.  Do not paper over unsupported platforms;
   fail closed with a clear error if required descriptor-relative primitives are
   unavailable.

Add deterministic regression tests for source-ancestor swap, memory-ancestor
swap if the helper is shared, static output-parent symlink, and output-parent
swap immediately before rename.  Each test must prove no external read/write
occurred and no apparently valid snapshot was published.  Preserve every
existing test.

Run focused state-sync plus shared-secret-path tests, `py_compile`, and
`git diff --check`.  Stop at `READY-FOR-PREFLIGHT` and wait for explicit
admission; do not start any full suite while ce-496 is active.

Standing preflight directive: run the FULL local validator preflight (`ce validate-pr`,
CI-parity) before every self-push or commit-for-harvest.  Do not discover gates via CI.

## Deliverable and stop line

After focused green, report exact changed paths and test evidence and stop at
`READY-FOR-PREFLIGHT`.  After a later explicit admission, run the actual
validator wrapper with `TMPDIR=/var/tmp`, a short fixed basetemp, credential
variables unset, and an explicit test command; commit only if fully green,
preserving dev-3 author and ce-dev-2 committer.  Stop on scope expansion or red.

