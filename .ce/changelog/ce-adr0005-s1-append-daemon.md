---
slug: ce-adr0005-s1-append-daemon
date: 2026-07-06
kind: feature
scope: validators
issue: ADR-0005
---

**Add mediated brain append worker skeleton.**

- Add data-only brain append intent envelope validation for active assertions and ce-411-style supersede pairs.
- Add a host-side one-intent worker skeleton that materializes origin/main, assigns ledger chain position through brain_runtime, and emits mediation evidence or fail-closed refusal artifacts.
