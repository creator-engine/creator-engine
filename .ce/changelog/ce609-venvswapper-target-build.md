---
slug: ce609-venvswapper-target-build
date: 2026-07-22
kind: changed
scope: runtime/update
issue: ce-ops#609
---

**Build VenvSwapper targets in place.**

- Build verified update and main-head virtual environments directly at their finalized target paths before the existing atomic live-symlink promotion. This preserves console-script interpreter paths and removes the staging-directory rename that left generated shims pointing at a removed path.
- Add end-to-end regression coverage for both routes, checking the `ce` and `cev3` interpreter lines after promotion.
