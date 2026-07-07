---
slug: ce-494-onboard-workflow-refresh
date: 2026-07-07
kind: fix
scope: validators
issue: ce-ops#494
---

**refresh stale onboarded workflow templates.**

Added a focused onboard workflow refresh mode that re-renders only the CE validation workflow for already-onboarded repos, no-ops when current, and teaches operators to run normal onboard first when the workflow is absent.
Added regression coverage for refresh behavior and workflow canonicalization parity with release publishing.
