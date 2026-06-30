---
slug: ce-370-local-preflight-pr-body
date: 2026-06-30
kind: fix
scope: validators
issue: ce-ops#370
---

**Local validate-pr honors PR body test-coupling exemptions.**

- Local `ce validate-pr` now sources PR body text for the test-coupling gate when available, matching CI exemption handling while preserving strict fallback behavior.
