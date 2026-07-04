---
slug: ce-422-tenant-record-schema
date: 2026-07-03
kind: added
scope: validator tenant records
issue: ce-ops#422
---

**Add tenant record schema and validator.**

- Added the `tenant-record` schema with closed-object validation for tenant identity, credential references, confidentiality posture, issue venue, fleet allocation, and governance ratification fields.
- Added the `tenant_record` validator check, a fictional well-formed tenant example, and focused unit coverage for required sections, pointer-only credential refs, unknown keys, enum failures, and ratification digest shape.
