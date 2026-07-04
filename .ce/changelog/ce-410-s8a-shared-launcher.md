---
slug: ce-410-s8a-shared-launcher
date: 2026-07-04
kind: story
scope: validation-runtime
issue: ce-ops#410
---

**slice 8a: shared container-launcher primitive.**

- Add a shared Podman launcher primitive for detached and foreground ephemeral container runs.
- Refactor worker allocation to consume the shared detached argv path without changing behavior.
