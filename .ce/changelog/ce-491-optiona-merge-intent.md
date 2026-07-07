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
- Revision: reconciled Option A with the tracked ce-488
  `brain_append_intent.schema.yaml` and `brain_append_worker.py`; specified the
  materialized ledger record schema, materialization-key persistence, HELD
  cascade, hard XOR gate, lease contract, topology question, dry-run/advisory
  evidence, merge-order discovery, and recovery semantics.
- Revision: clarified the PR #888 decision/lesson schema prerequisite and
  mapped decision/lesson intent payload fields to materialized memory records.
