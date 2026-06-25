---
slug: ce191-n5-fault-injection-failsafe
date: 2026-06-25
kind: fixed
scope: install fault-injection fail-safe
issue: ce-ops#191
---

**install fault-injection fail-safe (N5).**

- Clean fail-closed refusals (no traceback) on the apply/bootstrap path; missing deps during read-only --inventory surface as WARN rows (preserves N1).
