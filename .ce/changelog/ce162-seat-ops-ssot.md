---
slug: ce162-seat-ops-ssot
date: 2026-06-22
kind: added
scope: operator seat launch runbook sync
issue: ce-ops#162
work_class: feature
---

Adds the code-synced operator runbook for governed Claude and Codex seat
launches.

- Added an authoritative seat launch, governance, and containment runbook under
  `docs/operations/` with the Claude/Codex launch contract, credential boundary,
  isolated seat/container model, provisioning steps, governance attachment, and
  refusal remedies.
- Added a registered `operator_runbook_refusal_sync` validator check that
  derives expected `CC-D-*` and `CDX-D-*` clause IDs from the pure launcher spec
  modules and fails closed on malformed, missing, extra, or duplicate runbook
  clause entries.
- Added focused unit coverage for registration, current runbook sync, missing
  clauses, extra unknown clauses, and malformed/no clause block handling.
