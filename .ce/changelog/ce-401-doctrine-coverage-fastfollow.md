---
slug: ce-401-doctrine-coverage-fastfollow
date: 2026-07-05
kind: fix
scope: knowledge-ssot doctrine coverage
issue: ce-ops#401
---

**Harden doctrine coverage ratchet edge cases.**

- Treat an absent authoritative brain assertion ledger as empty coverage instead of corrupt or unreadable.
- Document the ratchet's linkage-only semantics and single-root live invocation decision.
- Add regression tests for duplicate exception entries and stale exceptions outside governed trees.
