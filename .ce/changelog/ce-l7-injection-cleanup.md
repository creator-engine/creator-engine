---
slug: ce-l7-injection-cleanup
date: 2026-06-30
kind: ci
scope: release
issue: ce-ops#0
---

**Harden release workflow GitHub expression injection boundaries.**

- **Declared work class:** tiny
- Moves release workflow GitHub expression values out of shell run blocks and into env indirection.
- Preserves release tag validation while removing direct expression interpolation from touched run blocks.
