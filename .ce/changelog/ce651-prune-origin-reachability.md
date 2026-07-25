---
slug: ce651-prune-origin-reachability
date: 2026-07-25
kind: fixed
scope: worktree prune safety
issue: CE-651
---

**Preserve archived worktree tips before pruning.**

- Worktree pruning refreshes `origin` with `git fetch --prune` once per scan
  before using a remote-tracking ref as preservation evidence. A failed or
  timed-out refresh leaves registered worktrees report-only, rather than
  trusting an unbounded stale cache.
- A clean old tip may be prunable when that fresh origin snapshot names a
  containing ref even if the tip is not an ancestor of `origin/main`; audit
  evidence names the satisfying ref.
- Tips absent from every freshly fetched origin ref are reported as
  `not-on-origin`, replacing the narrower `unpushed-commits` label. The remote
  can still change after a successful fetch, so freshness is bounded to scan
  time.
