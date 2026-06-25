---
slug: ce177-brain-drift-findings
date: 2026-06-25
kind: changed
scope: Structured Knowledge-SSOT drift findings
issue: ce-ops#177
---

**CE177 — structured brain-drift findings.**

- Add a `DriftFinding` (extends `ValidationError`) carrying `assertion_id`,
  `claimed`, `observed`, and optional `evidence_ref`, so a drift failure
  reports exactly which assertion diverged and how — not just that it did.
- Emit findings via `_drift_error(...)`; extend the offline tests accordingly.
