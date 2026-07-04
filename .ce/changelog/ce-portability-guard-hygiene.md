---
slug: ce-portability-guard-hygiene
date: 2026-07-04
kind: fix
scope: validators/tests/unit/test_portability_plane.py
issue: ce-ops#437
---

**Portability guard test hygiene.**

- Isolate runtime-only subprocess command fixtures.
- Add wrapper and absolute-path command fixtures.
- Document fail-closed runtime-command prose behavior.
- **Declared work class:** tiny
