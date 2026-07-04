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
