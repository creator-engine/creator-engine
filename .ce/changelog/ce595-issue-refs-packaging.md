---
slug: ce595-issue-refs-packaging
date: 2026-07-22
kind: changed
scope: validator portability
issue: ce-ops#595
---

**Package the canonical issue-reference parser.**

- Move the canonical issue-reference parser into the validator package; the reconciliation feed imports it directly while the legacy bare-checkout shim delegates through the canonical module, with wheel and editable-install coverage.
