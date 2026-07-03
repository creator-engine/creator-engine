---
slug: ce-410-conveyor-phase-authority
date: 2026-07-03
kind: changed
scope: conveyor
issue: ce-ops#410
---

**Type conveyor git runner phases and pass explicit subprocess envs.**

- Added conveyor-local git phase typing until authority_contexts.py lands.
- Routed local git and validation subprocesses through explicit, scrubbed env mappings.
