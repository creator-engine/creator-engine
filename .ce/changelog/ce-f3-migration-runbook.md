---
slug: ce-f3-migration-runbook
date: 2026-07-10
kind: feature
scope: controller-ops
---

**Codify controller migration completeness.**

Adds a controller migration completeness runbook covering role definitions,
memory, credentials, session infrastructure, and merge-gate topology with
acceptance evidence for each checklist item. Extends controller state snapshots
to carry `.claude/agents/*.md` role definitions through the manifest and
published snapshot tree so restored controllers can resolve worker roles before
dispatch.
