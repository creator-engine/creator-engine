---
slug: ce-433-confidentiality-surface-coverage
date: 2026-07-05
kind: story
scope: public-repo confidentiality push guard
issue: creator-engine/ce-ops#433
---

Adds an enforceable push-guard surface for the existing public-repo
confidentiality scanner.

- Reuses `public_docs_confidentiality` as the single rule source for working
  tree scans, commit-tree scans, and hook-style push checks.
- Adds `guard-public-docs-confidentiality-push`, a CLI seam that can be wired
  into local `pre-push` hooks or server-side `pre-receive` hooks.
- Scans pushed commit trees directly from git object IDs before refs are
  accepted, without checking out or mutating the worktree.
- Covers clean and leaking push-update cases in the existing confidentiality
  CLI test suite.
