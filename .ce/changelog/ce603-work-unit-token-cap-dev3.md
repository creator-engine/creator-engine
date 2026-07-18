---
slug: ce603-work-unit-token-cap-dev3
date: 2026-07-18
kind: feature
scope: runtime-governance
issue: ce-ops#603
---

Add a fail-closed, raw-token work-unit-cap design contract with canonical receipts,
ledger-backed reservations, and a verified-current-ledger A2/A3 predicate. The
predicate is inactive and deferred to a future named enforcement owner; this
change does not dispatch providers or activate a conveyor lifecycle.
