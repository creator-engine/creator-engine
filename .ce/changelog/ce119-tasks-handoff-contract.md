---
slug: ce119-tasks-handoff-contract
date: 2026-06-20
kind: added
scope: tasks handoff design
issue: ce-ops#119
---

Adds the ce-ops#119 design-pass contract for SHA-bound ratified task handoff
from Spec Kit tasks to governed worker seats.

- Documents the proposed `tasks.ce.yml` lifecycle, `do_not_replan` invariant,
  SHA drift gates, and mapping to existing Scope/Dispatch/brief machinery.
- Folds in the Operator-ratified decisions: emit only `tasks.ce.yml`, bind the
  full task set, keep worker completion evidence-only, materialize digests via
  the proposed `cev3 tasks bind`, and allow only breadth-capped scope globs.
- Adds a reference `schemas/tasks.schema.yaml` shape for Operator review.
- Leaves runtime and validator enforcement as explicitly deferred until the
  contract shape's later implementation pass.
