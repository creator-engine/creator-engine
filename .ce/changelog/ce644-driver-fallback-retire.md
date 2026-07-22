---
slug: ce644-driver-fallback-retire
date: 2026-07-22
kind: fixed
scope: ce-ops autoclose driver parser loading
issue: ce-ops#644
---

**Retire the autoclose driver inline fallback parser.**

- Remove the autoclose driver’s inline issue-reference grammar fallback. The tracked compatibility shim is now the only parser source; a checkout missing it fails closed with a value-free error.
- Add RED-to-GREEN coverage for the missing-shim deployment fault. Actions executes this integration-surface script from a full checkout, so live execution remains merge-time CI behavior.
