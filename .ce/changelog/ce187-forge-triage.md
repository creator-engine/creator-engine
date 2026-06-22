---
slug: ce187-forge-triage
ticket: ce-ops#187
type: feature
scope: autonomy triage front-half
---

Adds the first bounded forge-triage slice that turns explicit open-issue input
into deterministic pickup-ready work items for the existing belt.

- Adds an offline-first triage planner that emits claimable issues with pickup
  label and optional assignee mutations.
- Reuses the work-sizing ceremony for declared work-class and mutation-class
  records on each emitted item.
- Gates out blocked, dependency-blocked, already-assigned, arc-ticket, and
  active-work-claimed items before surfacing work to the belt.
- Wires `ce pickup triage` as a dry-run command by default, with explicit
  `--apply` for label/assignee mutations only and no lane launch path.
- Adds focused offline unit coverage for deterministic ordering, readiness
  gates, collision checks, sizing metadata, and CLI JSON output.
