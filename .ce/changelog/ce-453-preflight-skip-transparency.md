---
slug: ce-453-preflight-skip-transparency
date: 2026-07-05
kind: feature
scope: validators
issue: ce-ops#453
---

**preflight skipped-test transparency.**

- Report skipped tests from the PR preflight baseline-diff test gate with file counts and pytest -rs reasons when available.
- Keep skipped tests transparent rather than failing the preflight, and carry the skip count into the final PASS summary.
- Cover default, zero-skip, and contained-seat profile behavior.
