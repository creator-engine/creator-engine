---
slug: ce-368-test-coupling-gate
date: 2026-06-30
kind: added
scope: validator preflight
issue: ce-ops#368
---

**CE-native test-coupling validate-pr gate.**

Added a validate-pr PR-diff gate that blocks non-test source changes when the PR changes no tests.
