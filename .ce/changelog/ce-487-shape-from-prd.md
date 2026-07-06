---
slug: ce-487-shape-from-prd
date: 2026-07-06
kind: story
scope: shaping
issue: ce-ops#487
---

**PRD-aware shaping via ce shape --from.**

Adds `ce shape --from <path>` as a PRD/requirements context-injection path into the existing Shape grill.
The preview cites `Source PRD: <path>`, stays bounded to one Scope, and records nothing unless `--confirm` is supplied.
Updates CLI reference, product/architecture docs, and focused shaping tests.
