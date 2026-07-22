---
slug: ce609-venvswapper-target-build
date: 2026-07-22
kind: changed
scope: runtime/update
issue: ce-ops#609
---

**Build VenvSwapper targets in place.**

- Build verified update and main-head virtual environments directly at their finalized target paths before the existing atomic live-symlink promotion, preserving console-script interpreter paths.
- Cover recovery from a crashed partial build at the versioned final target on both routes; each regression proves the debris is removed before a clean rebuild and promotion.
