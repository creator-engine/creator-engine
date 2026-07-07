---
slug: ce-491-optiona-merge-intent
date: 2026-07-07
kind: changed
scope: docs
issue: ce-ops#491
---

**Design Option A merge-time brain append intent materialization.**

- Added a design-only proposal for post-merge materialization of
  `.ce/brain/append-intents/<branch-slug>.yaml` into the authoritative brain
  ledger.
- Covered owning actor recommendation, authority bounds, lifecycle,
  failure/crash handling, evidence, #882 stale-tail gate interaction, and drill
  coverage.

