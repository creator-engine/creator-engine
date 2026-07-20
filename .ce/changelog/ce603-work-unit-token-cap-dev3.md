---
slug: ce603-work-unit-token-cap-dev3
date: 2026-07-18
kind: feature
scope: runtime-governance
issue: ce-ops#603
---

Add fail-closed, raw-token work-unit advisory primitives with canonical receipts,
ledger-backed reservations, and read-only runtime evidence projection. CE603 does
not wire a production admission, conveyor, or provider caller, so it does not
enforce production dispatch; that wiring is explicitly outside this slice.
