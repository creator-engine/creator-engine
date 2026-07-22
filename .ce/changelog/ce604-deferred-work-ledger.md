---
slug: ce604-deferred-work-ledger
date: 2026-07-22
kind: added
scope: schema, seed, validator, and design-only belt wiring
issue: ce-ops#604
---

**Deferred-work ledger read-back ratchet.**

- Added the machine-readable deferred-work ledger with a schema-enforced four-way triage partition.
- Added a registered read-back ratchet so agent-resolvable residue cannot become a write-only archive.
- Bound read-back timestamps to creation order and a documented 300-second clock-skew allowance, with malformed top-level ledger inputs fail-closed.
- Added design-only re-feed guidance for the existing integrator belt; no belt, deployment, or workflow code changed.
- Registered the schema-reference inventory update required by the new tracked schema.
