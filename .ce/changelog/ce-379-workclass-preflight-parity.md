---
slug: ce-379-workclass-preflight-parity
date: 2026-07-01
kind: fix
scope: validators
issue: ce-379
---

**Local PR preflight mirrors canonical work-class names.**

- Keep `ce validate-pr` help and carrier errors aligned with `XS/S/M/L` while documenting legacy aliases.
- Add regression coverage proving canonical carrier lines and legacy aliases normalize through the same floor behavior.
