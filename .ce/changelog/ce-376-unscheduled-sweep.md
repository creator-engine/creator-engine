---
slug: ce-376-unscheduled-sweep
date: 2026-07-02
kind: fix
scope: forge-triage
issue: ce-ops#376
---

**Surface commissioned unscheduled issues in forge triage.**

- Add an advisory commissioned_unscheduled section to forge triage output.
- Mark commissioned_unscheduled_status as arc_missing when the payload lacks the arc issue.
- Keep dispatchable arc items unchanged and emit no mutations for the sweep section.
- Cover default and configurable commissioned predicates with unit tests.
