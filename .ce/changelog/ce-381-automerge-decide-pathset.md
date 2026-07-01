---
slug: ce-381-automerge-decide-pathset
date: 2026-07-01
kind: fix
scope: ci
issue: ce-ops#381
---

**Automerge decide uses PR-owned changed paths.**

- Resolve pull_request changed paths from the GitHub PR files API before falling
  back to a fetched-base three-dot git diff.
- Add workflow-level regression coverage for stale-base docs PR classification.
