---
slug: ce107b-sec7-forge-guard
date: 2026-06-26
kind: story
scope: hook and forge guards
issue: ce-ops#107(B)
---

**Section 7 forge guard.**

- **Declared work class:** story

- Added a shared §7 forge-operation guard and wired the hook, CLI, and direct forge adapters to deny governed-seat contexts before privileged forge operations.
- Added unit coverage for governed denial and non-governed/controller allowance across configure-repo, ruleset, review-submit, and auto-merge.
