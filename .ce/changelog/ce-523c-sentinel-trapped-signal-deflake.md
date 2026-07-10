---
slug: ce-523c-sentinel-trapped-signal-deflake
date: 2026-07-10
kind: fixed
scope: seat sentinel tests
---

**Deflake the trapped-signal sentinel wrapper test.**

- Synchronize the test with foreground-child creation before sending the
  whole-process-group signal, so SIGHUP deterministically exercises the
  wrapper trap rather than racing the child launch.
