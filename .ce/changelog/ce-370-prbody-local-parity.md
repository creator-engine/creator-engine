---
slug: ce-370-prbody-local-parity
date: 2026-07-02
kind: fix
scope: validators
issue: ce-ops#370
work_class: XS
---

**Local validate-pr test-coupling PR body parity.**

- Local `ce validate-pr` now passes explicit PR body files through to the test-coupling gate and falls back to the branch carrier when present, while staying strict when no local body source exists.
- Moved shared git helpers out of `work_sizing_floor` private symbols for reuse by test-coupling.
