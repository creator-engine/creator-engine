---
slug: ce-427-approver-ref-provenance
date: 2026-07-05
kind: story
scope: installer-schema
issue: ce-ops#427
---

**Approver ref provenance for installer ratification bindings.**

- Add optional approver_ref provenance to installer ratification bindings.
- Keep legacy bindings valid while validating malformed provenance fail-closed.
- Document that runtime-policy opt-out fragments keep only digest fields.
