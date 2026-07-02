---
slug: ce-391b-has-milestone-scalar
date: 2026-07-02
kind: fix
scope: validators
issue: ce-ops#391
---

**Fix forge triage milestone scalar classification.**

- Tightened `_has_milestone` scalar fallback so false-y unknown milestone shapes remain unmilestoned while truthy scalar references count as milestones.
- Added forge triage classification coverage for dict, list, `None`, empty string, bare string, and integer milestone payloads.
