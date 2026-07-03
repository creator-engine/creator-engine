---
slug: ce-407-pin-migration-s2
date: 2026-07-03
kind: changed
scope: brain assertion verification
issue: ce-ops#407
---

**Migrate integrator belt brain pins to probes.**

- Migrates d1b-10, d1b-11, and d1b-12 from integrator_belt.py hash pins to focused probe verification.
- Registers integrator belt probe checks and updates the authoritative brain drift ratchet.
