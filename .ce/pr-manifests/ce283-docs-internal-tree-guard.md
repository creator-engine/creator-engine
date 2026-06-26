---
slug: ce283-docs-internal-tree-guard
issue: ce-ops#283
declared_work_class: story
---

# PR path manifest - ce-ops#283 - docs internal-tree guard

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
This change adds a unit-test ratchet only; it does not register a validator
check.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=add52bbcf4dab9097fcf09911441fda11c30c8add486d2f71e0e56c0a6d4e4cb

```text
.ce/changelog/ce283-docs-internal-tree-guard.md
.ce/pr-manifests/ce283-docs-internal-tree-guard.md
PR_BODY.md
validators/tests/unit/test_public_docs_confidentiality.py
```
