---
slug: ce-440-s2-cev3-deprecation
date: 2026-07-04
kind: changed
scope: validator CLI
issue: creator-engine/ce-ops#440
---

**cev3 deprecation notice and internal-groups lock-in.**

- Adds a direct cev3 invocation deprecation notice while suppressing it for ce forwarding shims.
- Locks ce v3 forwarding shims out of internal-only command groups.
