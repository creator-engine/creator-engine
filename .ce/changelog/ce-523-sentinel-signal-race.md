---
slug: ce-523-sentinel-signal-race
date: 2026-07-10
kind: fixed
scope: seat sentinel tests
issue: ce-523
---

**Deflake the trapped-signal sentinel wrapper test.**

- Wait deterministically for the wrapper's trapped-signal `exited` record before
  asserting the exit contract, removing a parallel-runner timing race without
  weakening the required signal-derived exit code.
- Preserve the product signal that a killed seat still leaves reliable lifecycle
  evidence for harvest and operator diagnosis.
