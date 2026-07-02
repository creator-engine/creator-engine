---
slug: ce-369-fleet-guard-ssot-denylist
date: 2026-07-02
kind: validator
scope: fleet-manifest-guard
issue: ce-ops#369
---

**Fleet manifest guard uses identity registry denylist snapshot.**

- Derive the fleet manifest internal-identity denylist from a vendored snapshot generated from the private identity registry.
- Add a generator/freshness-check helper for maintainers with ce-ops access.
- Bound dev-1..dev-4 matching and narrow forge coverage to ce-kv-derived pointers.
