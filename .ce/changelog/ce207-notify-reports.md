---
slug: ce207-notify-reports
date: 2026-06-23
kind: added
scope: runner / notify-feed (CEO-mode status reports)
issue: ce-ops#207
---

Add a status-report notify event fold for the contact-on-need follow-up.

- Folds existing `runtime_run_outcome` records using the conserved run-outcome enum
  and existing spend-ledger records through the spend gate's fleet meter.
- Emits idempotent `status_report` notify events per report period through the
  existing desktop/exec/webhook sink path and notifier ledger.
- Reuses `shape_payload` for the new report payload, with an explicit allow-list so
  injected secrets in outcome or spend records do not reach report notifications.
