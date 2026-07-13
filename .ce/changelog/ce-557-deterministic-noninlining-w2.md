---
slug: ce-557-deterministic-noninlining-w2
date: 2026-07-13
kind: fixed
scope: validator tooling
issue: ce-ops#557
---

**Deterministic controller no-inlining enforcement.**

- Adds the required path-manifest and changelog carriers for the governed
  ce-ops#557 story on branch `ce-557-deterministic-noninlining-w2`.
- Records predecessor evidence from commit `3f451a284becebdc44672d84194e49cb949e1e00`:
  focused enforcement tests reported 263 passed, with the full validator
  previously blocked only on the missing path-manifest PR-diff gate.
