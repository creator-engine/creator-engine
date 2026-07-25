---
slug: ce651-prune-origin-reachability
date: 2026-07-25
kind: fixed
scope: worktree prune safety
issue: CE-651
---

**Preserve archived worktree tips before pruning.**

- Worktree pruning now accepts a clean old tip that is reachable from a local
  `origin/*` tracking ref, even if it is not an ancestor of `origin/main`.
- Ref-list and reachability probe errors remain report-only, and audit evidence
  names the origin ref that satisfied the durable-preservation check.
- Tips absent from every local origin tracking ref are reported as
  `not-on-origin`, replacing the narrower `unpushed-commits` label.
