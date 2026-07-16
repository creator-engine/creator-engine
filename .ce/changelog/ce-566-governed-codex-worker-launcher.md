---
slug: ce-566-governed-codex-worker-launcher
date: 2026-07-16
kind: epic
scope: governed Codex one-shot worker launcher
issue: ce-ops#566
---

**Add the policy-bound ce worker launch one-shot planner.**

- Adds canonical role-policy and SHA-256-verified brief delivery, the isolation matrix,
  pinned Codex model/effort argv, and fail-closed preflight.
- Removes caller launch-surface overrides; plans retain canonical paths/digests.
- Resolves the tracked VPS image source/digest while preserving exact-name removal, readiness, and diagnostics.
