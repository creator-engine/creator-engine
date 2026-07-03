---
slug: ce-407-pin-migration-s1
date: 2026-07-03
kind: changed
scope: brain assertion verification
issue: ce-ops#407
---

**Migrate pr_preflight brain pins to probes.**

- Migrates d1b-01, d1b-42, and d1b-43 from pr_preflight.py hash pins to focused probe verification.
- Registers pr_preflight probe checks and updates the authoritative brain drift ratchet.
