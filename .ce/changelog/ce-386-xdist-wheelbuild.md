---
slug: ce-386-xdist-wheelbuild
date: 2026-07-02
kind: fixed
scope: validator tests
issue: ce-ops#386
---

**Serialize wheelhouse built-surface wheel builds under xdist.**

- Mirrored the wheel-build xdist grouping style from test_wheel_bake.py on built-surface tests that invoke source wheel builds.
