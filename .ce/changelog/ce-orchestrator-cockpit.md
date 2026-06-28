---
slug: ce-orchestrator-cockpit
date: 2026-06-28
kind: added
scope: orchestrator cockpit
issue: ce-ops#616
---

**Orchestrator read-only cockpit status.**

- Adds a read-only `ce orchestrator status` command that summarizes local Orchestrator runtime records.
- Validates checkpoint, territory-map, harvest-packet, and operator-decision records before rendering human or JSON output.
- Documents and tests the new public command group without adding actuator behavior.
