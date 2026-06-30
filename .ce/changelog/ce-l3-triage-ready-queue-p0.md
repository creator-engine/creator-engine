---
slug: ce-l3-triage-ready-queue-p0
date: 2026-06-30
kind: added
scope: advisory ce-ops triage queue
---

Adds the P0 advisory Triage Ready Queue for inbound `creator-engine/ce-ops`
issues.

- New hidden `ce triage queue scan|inspect` commands classify recently updated
  open issues and render an advisory queue state.
- New `ce_ops_triage_queue` runtime reuses `forge_triage.normalize_issue`,
  `_infer_work_class`, `_infer_mutation_class`, and `readiness_blockers` instead
  of forking classification logic.
- Scheduled workflow runs every 30 minutes in dry-run mode by default, with
  manual `apply=true` available to patch an existing sentinel comment and upload
  local audit evidence.

The queue is advisory only: it does not ratify, approve, review, merge,
authorize dispatch, or block CI.
