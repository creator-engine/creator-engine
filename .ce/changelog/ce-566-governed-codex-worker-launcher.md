---
slug: ce-566-governed-codex-worker-launcher
date: 2026-07-16
kind: feature
scope: governed Codex one-shot worker launcher
issue: ce-ops#566
---

**Add the policy-bound ce worker launch one-shot planner.**

- Adds canonical role-policy plus SHA-256-verified brief delivery, a complete
  role-by-venue isolation matrix, the pinned Codex `0.145.0-alpha.9` model and
  effort argv, and executable/realpath/version fail-closed preflight.
- Removes caller policy, binary, stdin, output, flag, and add-dir replacement;
  dry-run plans retain only canonical paths and digests.
- Resolves the default VPS image source and immutable digest from the tracked
  surfaces manifest while preserving exact-container-name removal, readiness,
  and diagnostics without image-ancestor selectors.
