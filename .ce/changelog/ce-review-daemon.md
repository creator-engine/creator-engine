---
slug: ce-review-daemon
date: 2026-06-24
kind: added
scope: validator engine (forge.review_pickup) / ce CLI (review daemon)
issue: ce-ops#411
---

**Review-pickup DAEMON (ce-ops#411): autonomous fan-out of awaiting-review PRs to
distinct non-author reviewer seats, fail-closed.**

- `forge.review_pickup` adds `poll_review_pickup` / `run_review_pickup_loop`:
  find awaiting-review PRs in a scoped repo/org and request exactly one distinct
  non-author reviewer per PR that lacks a live non-author reviewer signal.
  Supports `--once` / `--loop` / `--dry-run`.
- Never routes a PR to its own author; refuses fail-closed on draft/unknown-draft
  state, missing author or head SHA, failed CI, unscoped query, or no distinct
  non-author reviewer candidate. Skips PRs that already carry a current
  non-author approval/objection or open review request. **Never merges — routing
  only.**
- Spreads multiple PRs across reviewer seats by load; `--dry-run` assigns nothing.
