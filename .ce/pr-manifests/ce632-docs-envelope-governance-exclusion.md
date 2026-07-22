# PR path manifest — ce-ops#632 · docs-envelope governance exclusion

This per-PR carrier lists the closed authorized path set for the `XS` slice.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=98657967f32b601524a79c1ea708c50a94cff25bbe4902b0cdcab1d26ce17e49

```text
.ce/changelog/ce632-docs-envelope-governance-exclusion.md
.ce/pr-manifests/ce632-docs-envelope-governance-exclusion.md
docs/decisions/ADR-0016-pre-delegated-merge-classes.md
validators/creator_engine_validator/forge/automerge_policy.py
validators/creator_engine_validator/forge/mutation_classifier.py
validators/tests/unit/test_automerge_policy.py
```
