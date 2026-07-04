---
slug: ce-n5-worktree-prune
date: 2026-07-04
kind: feature
scope: validators
issue: ce-ops#N5
---

**Add fail-safe worktree prune tool.**

- Added `ce worker worktree-prune` (dry-run by default; `--apply` required for destructive action).
- Classification uses three-dot content diff vs origin/main (not ancestry alone); dirty/unpushed worktrees are report-only, never touched.
- Fixes a self-delete defect found in internal review: apply_prune() previously only protected the primary worktree, not the actively-invoking linked worktree; now both are protected (see test_apply_never_removes_invocation_linked_worktree).
- Hardened invocation-worktree protection to derive independently from the process cwd (symlink-safe, walked to its containing worktree root), not just from `--repo-root`, so a `--repo-root`-pointed worktree A never causes removal of the cwd's own worktree B.
- Added `empty-tip-content` regression coverage (content-identical-but-diverged branch tip → prunable) and its inverse (diverged and non-empty tip content → `REPORT_ONLY`/`unpushed-commits`), proving the content check gates pruning, not ancestry.
- Locked registered worktrees are now surfaced as their own `REPORT_ONLY`/`locked` verdict.
