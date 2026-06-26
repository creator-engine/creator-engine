---
slug: ce241-contained-controller-parity
date: 2026-06-26
kind: added
scope: contained controller parity acceptance
issue: ce-ops#241
---

**Add contained controller parity acceptance harness.**

- Documented the C3 parity checklist for contained controller cutover.
- Added an offline validator harness for dispatch, merge-gate, daemon,
  operator-attach, credential-injection, and transport-free parity.
- Added unit coverage for checklist conformance, positive parity, and rejection
  paths for ambient credential reuse, wrong attach surfaces, and live transport.
