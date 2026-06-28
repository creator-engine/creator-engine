---
slug: ce-336-wheel-bake-tmp-isolation
date: 2026-06-28
kind: fixed
scope: wheel-bake validator tests
issue: ce-ops#336
---

**Isolate wheel-bake tmp build root.**

Build wheel-bake tests through an isolated temporary source root so stale
checkout-local `validators/build` artifacts cannot poison the gate.
