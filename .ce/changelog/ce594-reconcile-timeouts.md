---
slug: ce594-reconcile-timeouts
date: 2026-07-22
kind: changed
scope: ticket reconciliation
issue: ce-ops#594
---

**Bound stale-ticket reconciliation subprocesses.**

- The report-only reconciliation feed now bounds every GitHub API child call at 30.0 seconds and its workflow at 15 minutes; timeout failures are value-free and report no credentials or subprocess output.
