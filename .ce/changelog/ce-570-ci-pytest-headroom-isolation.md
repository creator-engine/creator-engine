---
slug: ce-570-ci-pytest-headroom-isolation
date: 2026-07-16
kind: fixed
scope: CI validation
issue: ce-ops#570
---

**CI pytest isolates nested disk-headroom checks.**

- Run the validator pytest suite with the existing nested-test headroom seam so GitHub-hosted runner capacity does not short-circuit preflight unit tests.
