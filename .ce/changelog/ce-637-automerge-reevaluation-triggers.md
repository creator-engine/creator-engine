---
slug: ce-637-automerge-reevaluation-triggers
date: 2026-07-20
kind: fix
scope: ci
issue: ce-ops#637
---

**Re-evaluate advisory automerge decisions when approval and validation state
can be complete.**

- Re-run the advisory decision after review submission and completion of the
  required `Validate` workflow.
- Keep fork-triggered execution on trusted repository code with the existing
  read-only token permissions and fail closed on ambiguous or stale PR state.
