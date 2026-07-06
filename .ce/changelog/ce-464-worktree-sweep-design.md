---
slug: ce-464-worktree-sweep-design
date: 2026-07-06
kind: added
scope: worktree-debt classified sweep design
issue: ce-ops#464
---

**Worktree-debt classified sweep design.**

- Added a design-only classified sweep proposal for accumulated `.ce/wt-*` and
  `/var/tmp/ce-*` directories.
- Defined deterministic classes, dry-run/default safety invariants, archive
  and undo-window apply flow, `ce worktree sweep` command shape, rollout, and a
  read-only appendix grounded in current host sample directories.
