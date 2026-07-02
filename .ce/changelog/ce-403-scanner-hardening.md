---
slug: ce-403-scanner-hardening
date: 2026-07-02
kind: fix
scope: validators
issue: ce-ops#403
---

**Harden public docs confidentiality scanner.**

- Harden the confidentiality scanner so stale baseline entries, empty scans, stat failures, and tracked-file enumeration failures fail closed.
- Add regression tests for duplicate generated carrier issue metadata and scanner failure paths.
