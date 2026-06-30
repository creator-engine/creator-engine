---
slug: ce-379-workclass-choices-compat
date: 2026-06-30
kind: fix
scope: validators
issue: ce-379
---

**Work-class validator choices accept canonical and legacy names.**

- Accept canonical XS/S/M/L and legacy tiny/story/feature/epic work-class inputs in validator preflight parser paths.
- Reuse the shared WORK_CLASS_INPUTS alias set and normalize through normalize_work_class.
