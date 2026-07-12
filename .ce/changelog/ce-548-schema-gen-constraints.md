---
slug: ce-548-schema-gen-constraints
date: 2026-07-12
kind: changed
scope: schema reference generation
issue: ce-ops#548
---

**Render direct numeric schema constraints in the generated reference.**

- Include `exclusiveMinimum`, `exclusiveMaximum`, and `multipleOf` when they occur directly on a projected field.
- Cover the three keywords with a copied-schema generation regression test.
