---
slug: ce-seat-preflight-parity
date: 2026-07-08
kind: task
scope: validators
---

Adjusted the seat-ready preflight profile so the control-plane portability guard is skipped for seat validation because seat-image runtime characteristics produce proven false failures, while the scan remains enforced by the default-profile preflight at controller harvest. Added unit coverage proving a simulated scanner failure does not fail the seat-ready profile and that the default profile still enforces the guard.
