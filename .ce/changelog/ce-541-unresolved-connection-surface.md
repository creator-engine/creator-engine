---
slug: ce-541-unresolved-connection-surface
date: 2026-07-12
kind: added
scope: onboard connection advisory surfaces
issue: ce-ops#541
---

**Surface unresolved onboarding connection.**

- Add a fail-closed, read-only projection of the most recent onboarding ledger invocation.
- Surface an unresolved forge identity connection in `ce status`, an advisory red/FAIL doctor
  line without changing doctor exits, and a stderr-only `ce launch` warning that preserves JSON.
- Cover exact-cascade recognition, clearing, unknown ledger states, and pre-spawn behavior.
