---
slug: ce-357-broker-decouple
date: 2026-06-29
kind: story
scope: product-lens
issue: ce-ops#357
---

**Decouple self-review broker from seat working trees.**

- Parameterizes the Surface-B self-review broker stable checkout path.
- Adds a fail-closed pinned checkout update helper and tests.
- Ensures broker imports prefer the configured stable checkout over seat working trees.
