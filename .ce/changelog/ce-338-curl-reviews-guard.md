---
slug: ce-338-curl-reviews-guard
date: 2026-06-27
kind: fix
scope: reviewer-authority hook guard
issue: ce-ops#338
---

**block raw curl PR review approvals through the reviewer-authority guard.**

- **Declared work class:** story

- Extends raw GitHub API approval detection from `gh api` to `curl` calls
  targeting `/pulls/<N>/reviews` with `event=APPROVE` bodies.
- Treats unreadable curl review bodies such as `@file` and `@-` as approval
  intent for fail-closed classification.
- Adds focused reviewer-authority coverage proving curl raw API APPROVE is
  denied with and without a matching PR review envelope.
