---
slug: ce258-stranded-pr-sweep
date: 2026-06-26
kind: feature
scope: conveyor stranded PR sweep
issue: ce-ops#258
---

Add a conveyor sweep for creator-engine PRs that are approved, green, clean, and
not already present in the `main` merge queue.

- Uses `repository.mergeQueue.entries(branch:"main")` membership, not
  `autoMergeRequest`, to decide whether a PR is already queued.
- Reuses the integrator approval reverify guard before enqueueing via
  `gh pr merge <n> --auto`.
- Excludes dirty or behind PRs and PRs whose required/rollup checks are not
  green.
- Exposes the cron-facing `ce conveyor sweep` command.
- **Declared work class:** story
