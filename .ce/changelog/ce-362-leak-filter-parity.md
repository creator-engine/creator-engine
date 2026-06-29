---
slug: ce-362-leak-filter-parity
date: 2026-06-29
kind: fix
scope: validator support agent
issue: ce-ops#362
---

**support-agent leak filter parity.**

- **Declared work class:** story
- Share one zero-leak rule table between the support runtime and eval harness.
- Extend secret-like environment token detection to `_PAT` and `_CMD` suffixes.
- Reject empty support eval case lists so an empty eval cannot report green.
