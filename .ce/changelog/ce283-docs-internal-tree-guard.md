---
slug: ce283-docs-internal-tree-guard
date: 2026-06-26
kind: added
scope: validators / public docs confidentiality
issue: ce-ops#283
---

**Add an internal-tree ratchet for public docs.**

`validators/tests/unit/test_public_docs_confidentiality.py` now fails when any
net-new file appears under `docs/operations/**` or `docs/delivery/**` unless it
is deliberately listed in the corresponding exception ratchet. The current
files are seeded so the guard passes today while preventing silent expansion of
internal operating and delivery material in the served docs tree.
