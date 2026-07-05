---
slug: ce-runner-helper-dedup
date: 2026-07-05
kind: changed
scope: runner docker gvisor translation
issue: ce-ops#447
---

**Deduplicate Docker runner translation helpers.**

- Hoist shared mount, policy-field, and launch-probe translation helpers into a public runner seam.
- Route both plain Docker and gVisor proxy backends through the shared helpers without changing rendered argv semantics.
