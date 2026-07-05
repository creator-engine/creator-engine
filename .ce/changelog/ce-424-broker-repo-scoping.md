---
slug: ce-424-broker-repo-scoping
date: 2026-07-05
kind: fix
scope: tools/egress-broker
issue: ce-ops#424
---

**Egress broker per-seat repo scoping.**

Added per-seat egress broker repo configuration with top-level repo fallback. Fail closed when a seat has no repo and no top-level default exists. Covered resolved-repo push, PR, and self-review request paths, and example config parsing.
