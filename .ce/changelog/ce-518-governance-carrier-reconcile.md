---
slug: ce-518-governance-carrier-reconcile
date: 2026-07-17
kind: changed
scope: validators
---

**Make stale-ticket reconciliation complete and canonical-parser aware.**

- Traverse open issues and merged pull requests through complete GraphQL
  repository connections before emitting advisory evidence.
- Suppress branch-only candidates already visible to the shared ce-ops parser,
  and keep repository credentials isolated by read surface.
- Add a daily/manual, report-only workflow with normalized dry-run artifacts.
