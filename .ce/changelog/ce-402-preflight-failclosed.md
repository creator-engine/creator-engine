---
slug: ce-402-preflight-failclosed
date: 2026-07-02
kind: fixed
scope: validator preflight
issue: ce-ops#402
---

**Fail closed when baseline-diff pytest does not execute tests.**

- Makes the validate-pr baseline-diff gate fail closed when pytest is missing, crashes, or collects zero tests.
- Preserves zero-new-failures behavior for genuine identical pytest failures after tests execute.
- authoring-doc line deferred -- rides the brain-migration lane
