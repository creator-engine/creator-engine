---
slug: ce-410-authority-contexts-core
date: 2026-07-03
kind: changed
scope: validators
issue: ce-ops#410
---

**Typed authority contexts for integrator credentials.**

- Added typed authority contexts for transport, local git, and validation sandbox boundaries.
- Removed process-global GH_TOKEN mutation from the integrator gh runner shim.
- Wired queue-poll and live action construction through explicit context values.
