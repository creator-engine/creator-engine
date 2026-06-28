---
slug: ce-orchestrator-record-schemas
date: 2026-06-28
kind: added
scope: orchestrator runtime records
issue: ce-ops#616
---

**Orchestrator runtime-record schemas.**

- Adds four Draft 2020-12 Orchestrator runtime-record schemas for checkpoints, territory maps, harvest packets, and operator decisions.
- Adds a standalone schema-backed validation helper with focused unit coverage for valid and invalid records.
- Keeps this slice unwired from CLI registries, broker, and existing orchestration modules.
