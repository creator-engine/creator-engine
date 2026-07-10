---
slug: ce-518s2-reconcile-feed
date: 2026-07-10
kind: added
scope: validators
---

**Add a report-only live feed for stale ticket reconciliation.**

- Added a thin `gh` adapter that collects open tickets and recently merged PRs
  into the frozen stale-ticket reconcile contract.
- Kept the sweep report-only: findings render as text or JSON, while only live
  collection failures produce a non-zero exit.
