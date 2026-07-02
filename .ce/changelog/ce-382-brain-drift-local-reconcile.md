---
slug: ce-382-brain-drift-local-reconcile
date: 2026-07-02
kind: fix
scope: validators
issue: ce-ops#382
---

**Local brain drift reconcile.**

- Add `ce brain sync` for idempotent local runtime reconciliation.
- Auto-reconcile ignored `.ce/state/brain` drift during local validate-pr when tracked `.ce/brain` sources are unchanged.
- Preserve canonical `.ce/brain` drift gating and add actionable remediation text.
