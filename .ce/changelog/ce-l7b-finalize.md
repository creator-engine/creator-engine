---
slug: ce-l7b-finalize
date: 2026-06-30
kind: added
scope: release automation
issue: L7/day-arc
---

**Finalize signed release publish workflow.**

- Adds a release-finalize workflow that verifies the Operator supplied public detached signature, copies finalized artifacts into docs/, and opens a release-publish PR.
- Adds guarded reviewer-token approval and auto-merge wiring for the publish PR.
- Covers the workflow with static unit contract tests.
