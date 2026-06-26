---
slug: ce-288-count-agnostic-checks
date: 2026-06-26
kind: fixed
scope: validator tests
issue: ce-ops#288
work_class: story
---

**fix(ce-ops#288): make registered-check assertions count-agnostic**

Replaced brittle absolute `registered_checks()` total assertions in forge and
registry unit tests with name-membership or non-membership assertions tied to
the module under test.
