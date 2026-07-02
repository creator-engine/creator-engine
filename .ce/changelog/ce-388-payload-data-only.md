---
slug: ce-388-payload-data-only
date: 2026-07-02
kind: fixed
scope: validators/conveyor-pickup
issue: ce-ops#388
---

**Enforce ADR-0004 data-only discovery payload schema.**

- Added an allowlist schema for conveyor discovery payloads that accepts only issue, branch_name, pr_title, and pr_body.
- Rejected unknown and authority-bearing control fields with value-free audit records.
